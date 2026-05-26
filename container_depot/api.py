"""
API Endpoints for Hermes/OpenClaw Agent Integration

These endpoints are designed to be consumed by the AI orchestrator
for WhatsApp/Telegram bot integration.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, cstr
import json
import base64
import hashlib

# ============================================================================
# Voucher / QR Code Validation
# ============================================================================

@frappe.whitelist(methods=["POST"], allow_guest=True)
def validate_qr(qr_data):
	"""
	Decode QR code and return voucher details.

	POST /api/v1/gate/validate-qr
	Body: { "qr_data": "QR_CODE_CONTENT" }

	Returns: {
		"valid": bool,
		"voucher_id": str,
		"voucher_type": str,
		"client": str,
		"payment_status": bool,
		"containers": list
	}
	"""
	try:
		# Find voucher by voucher_id (QR content should contain the ID)
		voucher = frappe.db.exists("Voucher", {"voucher_id": qr_data})

		if not voucher:
			# Try searching by partial match
			voucher = frappe.db.sql(
				"SELECT name FROM `tabVoucher` WHERE voucher_id LIKE %s LIMIT 1",
				f"%{qr_data}%"
			)
			if voucher:
				voucher = voucher[0][0]

		if not voucher:
			return {"valid": False, "error": "Voucher not found"}

		doc = frappe.get_doc("Voucher", voucher)

		return {
			"valid": True,
			"voucher_id": doc.voucher_id,
			"voucher_type": doc.voucher_type,
			"client": doc.client,
			"principal": doc.principal,
			"payment_status": doc.payment_status,
			"status": doc.status,
			"containers": [
				{
					"container_no": c.container_no,
					"status": c.status,
					"container_type": c.container_type
				}
				for c in doc.expected_containers
			]
		}

	except Exception as e:
		return {"valid": False, "error": str(e)}


# ============================================================================
# Gate Entry Operations
# ============================================================================

@frappe.whitelist(methods=["POST"], allow_guest=True)
def register_gate_entry(voucher_id, container_no, security_guard=None, truck_plate=None, driver_name=None):
	"""
	Log a container arrival at the gate.

	POST /api/v1/gate/entry
	Body: {
		"voucher_id": "VOUCH-XXXX",
		"container_no": "STLU123456-7",
		"security_guard": "user@company.com",
		"truck_plate": "ABC-1234",
		"driver_name": "John Doe"
	}

	Returns: {
		"success": bool,
		"gate_entry_id": str,
		"container_status": str
	}
	"""
	try:
		voucher = frappe.get_doc("Voucher", {"voucher_id": voucher_id})

		if not voucher:
			return {"success": False, "error": "Voucher not found"}

		if not voucher.payment_status:
			return {"success": False, "error": "Payment not verified for this voucher"}

		# Create or find Container
		container_name = frappe.db.get_value("Container", {"container_no": container_no.upper()})
		if not container_name:
			container = frappe.get_doc({
				"doctype": "Container",
				"container_no": container_no.upper(),
				"container_type": voucher.expected_containers[0].container_type if voucher.expected_containers else "ISO Tank",
				"status": "Gate_In",
				"principal": voucher.principal
			})
			container.insert(ignore_permissions=True)
			container_name = container.name
		else:
			container = frappe.get_doc("Container", container_name)

		# Create Gate Entry
		gate_entry = frappe.get_doc({
			"doctype": "Gate Entry",
			"voucher": voucher.name,
			"container": container_name,
			"container_no": container_no.upper(),
			"security_guard": security_guard or frappe.session.user,
			"truck_plate": truck_plate,
			"driver_name": driver_name,
			"gate_in_timestamp": now_datetime(),
			"inspection_status": "Pending"
		})
		gate_entry.insert(ignore_permissions=True)
		gate_entry.submit()

		# Update voucher container status
		for vc in voucher.expected_containers:
			if vc.container_no.upper() == container_no.upper():
				vc.status = "Gate_In"
				vc.gate_in_status = "Pending"
				voucher.save()
				break

		return {
			"success": True,
			"gate_entry_id": gate_entry.gate_entry_id,
			"container_no": container_no.upper(),
			"container_status": "Gate_In"
		}

	except Exception as e:
		return {"success": False, "error": str(e)}


# ============================================================================
# Yard Operations (Reachstacker)
# ============================================================================

@frappe.whitelist(methods=["GET"], allow_guest=True)
def get_pending_lifts(voucher_id=None, container_no=None):
	"""
	Get containers pending lift for a voucher.

	GET /api/v1/yard/pending-lifts?voucher_id=VOUCH-XXXX

	Returns: {
		"containers": [
			{
				"container_no": str,
				"status": str,
				"suggested_zone": str
			}
		]
	}
	"""
	try:
		containers = []

		if voucher_id:
			voucher = frappe.get_doc("Voucher", {"voucher_id": voucher_id})
			for vc in voucher.expected_containers:
				if vc.status in ["Expected", "Gate_In"]:
					containers.append({
						"container_no": vc.container_no,
						"status": vc.status,
						"container_type": vc.container_type,
						"suggested_zone": get_suggested_zone(vc.container_type, "Needs_Cleaning")
					})

		elif container_no:
			container = frappe.get_doc("Container", {"container_no": container_no.upper()})
			containers.append({
				"container_no": container.container_no,
				"status": container.status,
				"yard_zone": container.yard_zone
			})

		return {"success": True, "containers": containers}

	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist(methods=["PATCH"], allow_guest=True)
def update_container_location(container_no, yard_zone, lifted_by=None):
	"""
	Update container location after lift.

	PATCH /api/v1/yard/update-location
	Body: {
		"container_no": "STLU123456-7",
		"yard_zone": "Cleaning_Bay_C",
		"lifted_by": "reachstacker_operator"
	}

	Returns: {
		"success": bool,
		"container_no": str,
		"yard_zone": str
	}
	"""
	try:
		container = frappe.get_doc("Container", {"container_no": container_no.upper()})

		container.current_location = yard_zone
		container.yard_zone = yard_zone
		container.save(ignore_permissions=True)

		# Update voucher container if exists
		vouchers_active = frappe.db.get_all("Voucher", filters={"status": ("in", ["Active", "Partial"])}, pluck="name")
		voucher_name = None
		if vouchers_active:
			voucher_name = frappe.db.get_value(
				"Voucher Container",
				{"container_no": container_no.upper(), "parent": ("in", vouchers_active)},
				"parent"
			)
		if voucher_name:
			voucher = frappe.get_doc("Voucher", voucher_name)
			for vc in voucher.expected_containers:
				if vc.container_no.upper() == container_no.upper():
					vc.yard_location = yard_zone
					vc.lifted_by_reachstacker = lifted_by
					voucher.save(ignore_permissions=True)
					break

		return {
			"success": True,
			"container_no": container.container_no,
			"yard_zone": yard_zone
		}

	except Exception as e:
		return {"success": False, "error": str(e)}


def get_suggested_zone(container_type, service_type):
	"""Determine suggested yard zone based on container type and service"""
	if service_type == "Cleaning":
		return "Cleaning_Bay_C"
	elif service_type == "Repair":
		return "Workshop_D"
	elif service_type == "Survey":
		return "Survey_Lane_E"
	else:
		return "Storage_Yard_A"


# ============================================================================
# Inspection Operations
# ============================================================================

@frappe.whitelist(methods=["POST"], allow_guest=True)
def upload_inspection_evidence(container_no, photos, inspection_type="EIR-In", inspector=None):
	"""
	Receive inspection photos and save to storage.

	POST /api/v1/inspection/upload-evidence
	Body: {
		"container_no": "STLU123456-7",
		"photos": [
			{"view": "Front", "data": "base64_encoded_image"},
			{"view": "Back", "data": "base64_encoded_image"}
		],
		"inspection_type": "EIR-In"
	}

	Returns: {
		"success": bool,
		"inspection_id": str,
		"photo_urls": list
	}
	"""
	try:
		# Find or create inspection record
		container = frappe.get_doc("Container", {"container_no": container_no.upper()})

		inspection = frappe.get_doc({
			"doctype": "Inspection",
			"container": container.name,
			"container_no": container.container_no,
			"inspection_type": inspection_type,
			"inspector": inspector or frappe.session.user,
			"status": "Draft"
		})
		inspection.insert(ignore_permissions=True)

		# Save photos
		photo_urls = []
		for photo in photos:
			# In production, save to S3 and get URL
			# For now, just record the reference
			photo_url = f"/files/inspection/{container_no}/{photo.get('view', 'Unknown')}.jpg"

			inspection.append("exterior_photos", {
				"photo_view": photo.get("view", "Other"),
				"photo_url": photo_url,
				"timestamp": now_datetime(),
				"uploaded_by": inspector or frappe.session.user
			})
			photo_urls.append(photo_url)

		inspection.save()

		return {
			"success": True,
			"inspection_id": inspection.inspection_id,
			"photo_urls": photo_urls
		}

	except Exception as e:
		return {"success": False, "error": str(e)}


# ============================================================================
# Helper Functions
# ============================================================================

def generate_qr_code(voucher_id):
	"""Generate QR code image for a voucher"""
	import qrcode
	from io import BytesIO
	import base64

	qr_data = f"OAK|{voucher_id}"

	img = qrcode.make(qr_data)
	buffered = BytesIO()
	img.save(buffered, format="PNG")

	return base64.b64encode(buffered.getvalue()).decode()


# ============================================================================
# WhatsApp/Telegram Webhook Handlers
# ============================================================================

@frappe.whitelist(methods=["POST"], allow_guest=True)
def handle_webhook(platform=None, message=None, from_user=None, from_number=None, session_id=None):
	"""
	Handle incoming messages from WhatsApp/Telegram.

	POST /api/v1/webhook/message
	Body: {
		"platform": "whatsapp" | "telegram",
		"from_user": "user_id or phone number",
		"from_number": "+1234567890",
		"message": "Container STLU123456-7 status",
		"session_id": "optional-session-id"
	}

	Returns agent response based on natural language intent.
	"""
	try:
		platform = platform or "whatsapp"
		from_user = from_user or frappe.session.user

		# Create or update session
		if not session_id:
			session_id = f"{platform}_{from_user}_{now_datetime().strftime('%Y%m%d')}"

		intent = detect_intent(message)
		response = process_intent(intent, message, from_user, session_id)

		return {
			"success": True,
			"session_id": session_id,
			"intent": intent,
			"response": response
		}

	except Exception as e:
		return {"success": False, "error": str(e)}


def detect_intent(message):
	"""Detect user intent from natural language message"""
	message_lower = message.lower() if message else ""

	intents = {
		"check_status": ["status", "where is", "location", "check container", "container location"],
		"gate_in": ["gate in", "arrival", "arrive", "check in"],
		"gate_out": ["gate out", "departure", "depart", "check out", "release"],
		"upload_photo": ["upload", "photo", "picture", "image", "inspection"],
		"check_payment": ["payment", "paid", "voucher", "bon"],
		"cleaning_queue": ["cleaning", "clean", "queue", "bay"],
		"repair_status": ["repair", "damage", "fix", "gasket"],
		"help": ["help", "what can", "commands", "menu"]
	}

	for intent, keywords in intents.items():
		if any(keyword in message_lower for keyword in keywords):
			return intent

	return "unknown"


def process_intent(intent, message, from_user, session_id):
	"""Process detected intent and return appropriate response"""

	intent_handlers = {
		"check_status": handle_check_status,
		"gate_in": handle_gate_in,
		"gate_out": handle_gate_out,
		"upload_photo": handle_upload_photo,
		"check_payment": handle_check_payment,
		"cleaning_queue": handle_cleaning_queue,
		"repair_status": handle_repair_status,
		"help": handle_help,
		"unknown": handle_unknown
	}

	handler = intent_handlers.get(intent, handle_unknown)
	return handler(message, from_user, session_id)


def handle_check_status(message, from_user, session_id):
	"""Handle container status check"""
	# Extract container number from message
	import re
	container_match = re.search(r'([A-Z]{4}\d{6}-?\d)', message)

	if not container_match:
		return "Please provide a container number (e.g., STLU123456-7). What container would you like to check?"

	container_no = container_match.group(1)
	container = frappe.db.exists("Container", {"container_no": container_no.upper()})

	if not container:
		return f"Container {container_no} not found in the system."

	doc = frappe.get_doc("Container", container)

	response = f"*Container Status: {doc.container_no}*\n"
	response += f"Status: {doc.status.replace('_', ' ')}\n"
	response += f"Location: {doc.current_location or 'Not assigned'}\n"
	response += f"Principal: {doc.principal or 'N/A'}\n"

	if doc.status == "Needs_Cleaning":
		response += f"\n⚠️ Container is pending cleaning. Please proceed to inspection."
	elif doc.status == "Cleaning":
		response += f"\n🧹 Container is currently being cleaned."
	elif doc.status == "Ready":
		response += f"\n✅ Container is ready for gate-out."

	return response


def handle_gate_in(message, from_user, session_id):
	"""Handle gate-in registration"""
	# Extract voucher and container from message
	import re

	voucher_match = re.search(r'VOUCH-[A-Z0-9]+', message.upper())
	container_match = re.search(r'([A-Z]{4}\d{6}-?\d)', message)

	if not voucher_match:
		return "Please provide a voucher number (e.g., VOUCH-ABCD1234) to proceed with gate-in."

	voucher_id = voucher_match.group(0)
	voucher = frappe.db.exists("Voucher", {"voucher_id": voucher_id})

	if not voucher:
		return f"Voucher {voucher_id} not found. Please verify the voucher number."

	voucher_doc = frappe.get_doc("Voucher", voucher)

	if not voucher_doc.payment_status:
		return "⚠️ Payment not verified for this voucher. Please contact the office."

	if not container_match:
		return "Please provide the container number (e.g., STLU123456-7) that has arrived."

	container_no = container_match.group(1)

	# Register gate entry
	result = register_gate_entry(
		voucher_id=voucher_id,
		container_no=container_no,
		security_guard=from_user
	)

	if result.get("success"):
		return f"✅ Gate-in registered successfully!\n\nContainer: {container_no}\nStatus: {result.get('container_status')}\n\nNext step: Proceed to inspection bay for EIR-In."
	else:
		return f"❌ Gate-in failed: {result.get('error')}"


def handle_gate_out(message, from_user, session_id):
	"""Handle gate-out process"""
	import re

	container_match = re.search(r'([A-Z]{4}\d{6}-?\d)', message)

	if not container_match:
		return "Please provide a container number (e.g., STLU123456-7) for gate-out."

	container_no = container_match.group(1)
	container = frappe.db.exists("Container", {"container_no": container_no.upper()})

	if not container:
		return f"Container {container_no} not found."

	doc = frappe.get_doc("Container", container)

	if doc.status != "Ready":
		return f"⚠️ Container {container_no} is not ready for gate-out.\nCurrent status: {doc.status.replace('_', ' ')}\n\nPlease complete all required services first."

	response = f"✅ Container {container_no} is ready for gate-out.\n\n"
	response += "Please proceed to gate with the release voucher.\n"
	response += "Final inspection (EIR-Out) photos will be required."

	return response


def handle_upload_photo(message, from_user, session_id):
	"""Handle inspection photo upload"""
	return "📸 Photo upload feature. Please send the inspection photos along with:\n\n" \
	       "1. Container number (e.g., STLU123456-7)\n" \
	       "2. Photo view (Front/Back/Left/Right)\n" \
	       "3. Any damage notes (if applicable)"


def handle_check_payment(message, from_user, session_id):
	"""Handle payment/voucher check"""
	import re

	voucher_match = re.search(r'VOUCH-[A-Z0-9]+', message.upper())

	if not voucher_match:
		return "Please provide a voucher number (e.g., VOUCH-ABCD1234) to check payment status."

	voucher_id = voucher_match.group(0)
	voucher = frappe.db.exists("Voucher", {"voucher_id": voucher_id})

	if not voucher:
		return f"Voucher {voucher_id} not found."

	doc = frappe.get_doc("Voucher", voucher)

	response = f"*Voucher Details: {doc.voucher_id}*\n"
	response += f"Type: {doc.voucher_type.replace('_', ' ')}\n"
	response += f"Client: {doc.client}\n"
	response += f"Principal: {doc.principal or 'N/A'}\n"

	if doc.payment_status:
		response += f"\n✅ Payment: VERIFIED\n\nYou may proceed with gate-in."
	else:
		response += f"\n❌ Payment: PENDING\n\nPlease complete payment before gate-in."

	if doc.expected_containers:
		response += f"\n\n*Containers:*\n"
		for c in doc.expected_containers:
			response += f"- {c.container_no}: {c.status.replace('_', ' ')}\n"

	return response


def handle_cleaning_queue(message, from_user, session_id):
	"""Handle cleaning queue check"""
	# Get pending cleaning orders
	cleaning_orders = frappe.db.sql("""
		SELECT name, container, priority, status, created_at
		FROM `tabCleaning Order`
		WHERE status = 'Pending'
		ORDER BY priority DESC, created_at ASC
		LIMIT 10
	""", as_dict=True)

	if not cleaning_orders:
		return "🧹 No containers currently pending cleaning."

	response = "*Cleaning Queue (Pending):*\n\n"
	for i, order in enumerate(cleaning_orders, 1):
		response += f"{i}. Container: {order.container}\n"
		response += f"   Priority: {order.priority} | Status: {order.status}\n\n"

	return response


def handle_repair_status(message, from_user, session_id):
	"""Handle repair status check"""
	import re

	container_match = re.search(r'([A-Z]{4}\d{6}-?\d)', message)

	if not container_match:
		return "Please provide a container number (e.g., STLU123456-7) to check repair status."

	container_no = container_match.group(1)
	container = frappe.db.exists("Container", {"container_no": container_no.upper()})

	if not container:
		return f"Container {container_no} not found."

	doc = frappe.get_doc("Container", container)

	response = f"*Repair Status: {container_no}*\n"
	response += f"Current Status: {doc.status.replace('_', ' ')}\n"

	if doc.status == "Needs_Repair":
		response += f"\n⚠️ Container needs repair.\n"
		response += f"Location: {doc.current_location or 'Workshop'}\n"
	elif doc.status == "Repairing":
		response += f"\n🔧 Repair in progress.\n"
		response += f"Location: {doc.current_location or 'Workshop'}\n"
	else:
		response += f"\nNo active repair work.\n"

	return response


def handle_help(message, from_user, session_id):
	"""Handle help request"""
	return """🤖 *Oak Depot Assistant - Help Menu*

*Available Commands:*

📍 *Check Status*
   "What is the status of STLU123456-7?"
   "Where is container ABCD123456-7?"

🚪 *Gate-In*
   "Gate in STLU123456-7 with voucher VOUCH-ABCD1234"
   "Container arrived, voucher VOUCH-ABCD1234"

💰 *Check Payment*
   "Check payment for VOUCH-ABCD1234"
   "Is VOUCH-ABCD1234 paid?"

🧹 *Cleaning Queue*
   "Show cleaning queue"
   "What's in the cleaning bay?"

🔧 *Repair Status*
   "Repair status for STLU123456-7"

📸 *Upload Photos*
   "Upload inspection photo for STLU123456-7"

❓ *Help*
   "Help" or "What can you do?"

*Tip:* Always include container numbers (e.g., STLU123456-7) or voucher numbers (e.g., VOUCH-ABCD1234) in your messages.
"""


def handle_unknown(message, from_user, session_id):
	"""Handle unrecognized intent"""
	return """🤔 I'm not sure what you're asking for.

Please try one of these:
- "Check status of STLU123456-7"
- "Gate in with voucher VOUCH-ABCD1234"
- "Check payment for VOUCH-ABCD1234"
- "Show cleaning queue"
- "Help" for more commands
"""


# ============================================================================
# Agent Skills Definition (for Hermes/OpenClaw)
# ============================================================================

@frappe.whitelist(methods=["GET"], allow_guest=True)
def get_agent_skills():
	"""
	Return available agent skills for the Hermes/OpenClaw integration.

	GET /api/v1/agent/skills

	Returns: {
		"skills": [
			{
				"name": "validate_qr",
				"endpoint": "/api/v1/gate/validate-qr",
				"method": "POST",
				"description": "Validate QR code and return voucher details",
				"parameters": ["qr_data"]
			},
			...
		]
	}
	"""
	skills = [
		{
			"name": "validate_qr",
			"endpoint": "/api/v1/gate/validate-qr",
			"method": "POST",
			"description": "Decode QR code and validate voucher. Returns voucher details including payment status and expected containers.",
			"parameters": ["qr_data"]
		},
		{
			"name": "register_gate_entry",
			"endpoint": "/api/v1/gate/entry",
			"method": "POST",
			"description": "Register container gate-in at security checkpoint. Creates gate entry record and updates container status.",
			"parameters": ["voucher_id", "container_no", "security_guard", "truck_plate", "driver_name"]
		},
		{
			"name": "get_pending_lifts",
			"endpoint": "/api/v1/yard/pending-lifts",
			"method": "GET",
			"description": "Get list of containers pending lift for a voucher. Returns container numbers, status, and suggested yard zones.",
			"parameters": ["voucher_id", "container_no"]
		},
		{
			"name": "update_container_location",
			"endpoint": "/api/v1/yard/update-location",
			"method": "PATCH",
			"description": "Update container yard location after reachstacker lift. Updates both container and voucher records.",
			"parameters": ["container_no", "yard_zone", "lifted_by"]
		},
		{
			"name": "upload_inspection_evidence",
			"endpoint": "/api/v1/inspection/upload-evidence",
			"method": "POST",
			"description": "Upload inspection photos (EIR-In/EIR-Out). Saves photos and returns URLs.",
			"parameters": ["container_no", "photos", "inspection_type", "inspector"]
		},
		{
			"name": "handle_webhook",
			"endpoint": "/api/v1/webhook/message",
			"method": "POST",
			"description": "Process natural language messages from WhatsApp/Telegram. Auto-detects intent and routes to appropriate handler.",
			"parameters": ["platform", "message", "from_user", "from_number", "session_id"]
		},
		{
			"name": "get_agent_skills",
			"endpoint": "/api/v1/agent/skills",
			"method": "GET",
			"description": "Return available agent skills and endpoint definitions for integration.",
			"parameters": []
		}
	]

	return {"success": True, "skills": skills}
