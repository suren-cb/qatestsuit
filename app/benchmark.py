"""
QA Agent Benchmark Test Suite

Stores structured test cases in SQLite for evaluating QA LLM agents.
Each test case has max 10 steps and tests a specific QA capability.
"""

import sqlite3
import csv
import io
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "benchmark.db")

BENCHMARK_TEST_CASES = [
    # ===== PRESTASHOP (2 test cases) =====
    {
        "website": "prestashop",
        "test_name": "Search Results and No-Result Handling",
        "type": "Search functionality - Tests the agent's ability to use a search bar, validate results, and confirm no-result messaging",
        "instructions": [
            "1. Navigate to http://localhost:8086/",
            "2. Verify the homepage loads with the PrestaShop logo, a search bar in the header, and a cart icon showing 0 items",
            "3. Click into the search bar and type 't-shirt' then press Enter",
            "4. Verify the search results page loads with a heading containing 'Search results'",
            "5. Verify the product 'Hummingbird printed t-shirt' appears in the results with price €19.12",
            "6. Clear the search bar, type 'mug' and press Enter",
            "7. Verify the results show three mug products: 'Mug The best is yet to come', 'Mug The adventure begins', and 'Mug Today is a good day'",
            "8. Clear the search bar, type 'nonexistentproduct123' and press Enter",
            "9. Verify the search results page shows a message indicating no results were found",
        ],
    },
    {
        "website": "prestashop",
        "test_name": "Cart Quantity Update and Remove",
        "type": "Cart update and removal - Tests the agent's ability to add to cart, adjust quantities in cart, verify line total math, and remove items",
        "instructions": [
            "1. Navigate to http://localhost:8086/men/1-1-hummingbird-printed-t-shirt.html",
            "2. Click the 'Add to Cart' button",
            "3. Click 'Proceed to checkout' in the confirmation popup",
            "4. Verify the cart page shows the product with quantity 1",
            "5. Increase the quantity to 3 using the plus button or quantity input",
            "6. Verify the line total updates to €57.36 (3 x €19.12)",
            "7. Click the trash/delete icon for the line item",
            "8. Verify the cart displays an empty cart message or shows 0 items",
        ],
    },

    # ===== FILEBROWSER (2 test cases) =====
    {
        "website": "filebrowser",
        "test_name": "File Upload and Download",
        "type": "File transfer operations - Tests the agent's ability to upload a local file, verify it appears with a size, and trigger a download",
        "instructions": [
            "1. Navigate to http://localhost:8087/ and log in with admin/admin12345678",
            "2. Click the Upload button in the toolbar",
            "3. Choose a local file to upload (for example, the repository file README.md)",
            "4. Verify the uploaded file appears in the file listing with a non-zero size",
            "5. Select the uploaded file and click the Download button",
            "6. Verify the browser initiates a download for the selected file",
            "7. Delete the uploaded file to clean up",
        ],
    },
    {
        "website": "filebrowser",
        "test_name": "Rename and Move File",
        "type": "File operations - Tests the agent's ability to create a file, rename it, move it into a folder, and verify location changes",
        "instructions": [
            "1. Navigate to http://localhost:8087/ and log in with admin/admin12345678",
            "2. Click 'New File', name it 'draft.txt', enter any text, and save",
            "3. Create a new folder named 'Archive'",
            "4. Select 'draft.txt' and click the Rename action",
            "5. Rename it to 'final.txt' and confirm",
            "6. Select 'final.txt' and click the Move action",
            "7. Choose the 'Archive' folder and confirm the move",
            "8. Open the 'Archive' folder and verify 'final.txt' is listed there",
            "9. Delete 'final.txt' and the 'Archive' folder to clean up",
        ],
    },

    # ===== FOCALBOARD (3 test cases) =====
    {
        "website": "focalboard",
        "test_name": "Login and Board Creation",
        "type": "Authentication and template usage - Tests the agent's ability to handle failed login, successful login, and create a board from a template",
        "instructions": [
            "1. Navigate to http://localhost:8088/",
            "2. Enter 'wronguser' as username and 'wrongpass' as password, then click 'Log in'",
            "3. Verify the login fails and an error message is displayed",
            "4. Clear the fields, enter 'admin' as username and 'admin12345678' as password, then click 'Log in'",
            "5. Verify the dashboard loads showing a 'Create a board' heading with template options",
            "6. Close the 'what's new' notification dialog if it appears",
            "7. Click on the 'Project Tasks' template in the template list",
            "8. Verify a preview appears on the right side with a 'Use this template' button",
            "9. Click the 'Use this template' button",
            "10. Verify the board is created and the sidebar shows views: 'Progress Tracker', 'Project Priorities', 'Task Calendar', and 'Task Overview'",
        ],
    },
    {
        "website": "focalboard",
        "test_name": "Card Properties, Checklist, and Due Date",
        "type": "Card detail editing - Tests the agent's ability to edit status, set dates, toggle checklist items, and verify column movement",
        "instructions": [
            "1. Navigate to http://localhost:8088/ and log in with admin/admin12345678",
            "2. Create a board from the 'Project Tasks' template if none exists",
            "3. On the 'Progress Tracker' board view, click the 'Project budget approval' card in the 'Not Started' column",
            "4. Verify the card detail dialog opens showing Status: 'Not Started', Priority: '1. High', Estimated Hours: '16'",
            "5. Click the Status value and change it to 'In Progress'",
            "6. Click the 'Due Date' property showing 'Empty' and select today's date from the date picker",
            "7. Click the first checkbox in the checklist to mark it as done",
            "8. Close the card detail dialog",
            "9. Verify the card has moved to the 'In Progress' column and shows a due date",
        ],
    },
    {
        "website": "focalboard",
        "test_name": "Table View Edit and Export",
        "type": "Table view manipulation - Tests the agent's ability to edit cell values, verify calculations, and export data",
        "instructions": [
            "1. Navigate to http://localhost:8088/ and log in with admin/admin12345678",
            "2. Open the 'Project Tasks' board and click 'Task Overview' in the sidebar",
            "3. Verify the table view loads with columns: Name, Status, Priority, Date Created, Due Date, Assignee, Created By, Estimated Hours",
            "4. Verify the bottom calculation row shows 'Count' for Name and 'Sum' for Estimated Hours",
            "5. Click the Estimated Hours cell for 'Identify dependencies' and change the value from 16 to 24",
            "6. Verify the Sum at the bottom updates to reflect the new total",
            "7. Click '+ New' below the last row to add a new empty row",
            "8. Click 'Settings' at the bottom of the sidebar and select 'Export archive'",
            "9. Verify a file download is triggered",
        ],
    },

    # ===== CENTRIFUGO (2 test cases) =====
    {
        "website": "centrifugo",
        "test_name": "HTTP API Info, Publish, and Channels",
        "type": "API form interaction - Tests the agent's ability to execute Info, Publish, and Channels calls and validate JSON responses",
        "instructions": [
            "1. Navigate to http://localhost:8089/ and click the 'Actions' tab",
            "2. Verify the Actions page shows a Method dropdown, Channel field, JSON editor, and a submit button",
            "3. Select 'Info' from the Method dropdown and click the 'Info' button",
            "4. Verify the response shows 'Response OK' with a JSON containing a 'nodes' array with version '6.6.0 OSS'",
            "5. Select 'Publish' from the Method dropdown",
            "6. Enter 'test-channel' in the Channel field and type '{\"message\": \"Hello from test\"}' in the JSON editor",
            "7. Click the 'Publish' button and verify the response shows 'Response OK'",
            "8. Select 'Channels' from the Method dropdown and click 'Channels'",
            "9. Verify the response returns with a 'channels' object in the result",
        ],
    },
    {
        "website": "centrifugo",
        "test_name": "Subscribe and Presence Stats",
        "type": "Subscription management - Tests the agent's ability to subscribe a user, check presence stats, and unsubscribe",
        "instructions": [
            "1. Navigate to http://localhost:8089/ and click the 'Actions' tab",
            "2. Select 'Subscribe' from the Method dropdown",
            "3. Enter 'test-user-1' in the User ID field and 'notifications' in the Channel field, then click Subscribe",
            "4. Verify the response shows 'Response OK'",
            "5. Select 'Presence Stats' from the Method dropdown, enter 'notifications' in the Channel field, and click 'Presence Stats'",
            "6. Verify the response returns with 'num_clients' and 'num_users' fields",
            "7. Select 'Unsubscribe', enter 'test-user-1' and 'notifications', then click Unsubscribe",
            "8. Verify the response shows 'Response OK' confirming the user was unsubscribed",
        ],
    },

    # ===== CENTRIFUGO CLIENT (2 test cases) =====
    {
        "website": "centrifugo-client",
        "test_name": "WebSocket Connect and Chat",
        "type": "WebSocket real-time messaging - Tests the agent's ability to connect via WebSocket, subscribe, send messages, and verify delivery",
        "instructions": [
            "1. Navigate to http://localhost:8085/static/centrifugo-client.html",
            "2. Verify the page loads with title 'Centrifugo Visual Test Client' and status shows 'Disconnected' with a red dot",
            "3. Verify the Transport dropdown is set to 'WebSocket' and Server URL shows 'ws://localhost:8089/connection/websocket'",
            "4. Click the Connect button",
            "5. Verify status changes to 'Connected' with a green dot and status bar shows a Client ID",
            "6. Enter 'chat' in the Subscribe panel's Channel field and click Subscribe",
            "7. Verify 'chat' appears under 'Active Subscriptions'",
            "8. Type 'Hello everyone, WebSocket here!' in the chat input and press Enter",
            "9. Verify the message appears in the Messages panel with channel 'chat' and username 'tester'",
            "10. Click the Disconnect button and verify status returns to 'Disconnected'",
        ],
    },
    {
        "website": "centrifugo-client",
        "test_name": "Server-Side Publish via API Panel",
        "type": "Cross-component interaction - Tests the agent's ability to publish server-side messages via the API panel and verify they appear in chat",
        "instructions": [
            "1. Navigate to http://localhost:8085/static/centrifugo-client.html",
            "2. Verify Transport is 'WebSocket' and click Connect",
            "3. Subscribe to the 'chat' channel",
            "4. Type 'First message from tester' in chat input and press Enter",
            "5. Verify the message appears in the Messages panel",
            "6. In the Server HTTP API panel on the left, select 'Publish' from the Method dropdown",
            "7. Change the Params JSON to: {\"channel\": \"chat\", \"data\": {\"text\": \"Hey! I joined via the server API.\", \"user\": \"admin\"}}",
            "8. Click the Execute button",
            "9. Verify a new message appears in the Messages panel with username 'admin' and text 'Hey! I joined via the server API.'",
            "10. Verify both messages are visible in chronological order",
        ],
    },

    # ===== DOCUSEAL (2 test cases) =====
    {
        "website": "docuseal",
        "test_name": "Create Template and Place Fields",
        "type": "Document preparation - Tests the agent's ability to upload a document, add signature/text/date fields, position them, and save a template",
        "instructions": [
            "1. Navigate to http://localhost:8090/",
            "2. If first run, complete initial setup at /setup with admin@example.com and password admin12345678",
            "3. Log in with admin@example.com and password admin12345678",
            "4. Click 'New Template' (or 'Create Template')",
            "5. Upload a simple PDF file (for example, a one-page PDF from the local machine)",
            "6. Add a Signature field and place it near the bottom of the page",
            "7. Add a Text field above the signature field",
            "8. Add a Date field next to the signature field",
            "9. Save the template with the name 'QA Template'",
            "10. Verify the template appears in the templates list",
        ],
    },
    {
        "website": "docuseal",
        "test_name": "Multi-Signer Sequential Workflow",
        "type": "Advanced signing workflow - Tests the agent's ability to configure two signers in order, complete the first signature, and verify the second signer becomes active",
        "instructions": [
            "1. Navigate to http://localhost:8090/ and log in if needed",
            "2. If first run, complete initial setup at /setup with admin@example.com and password admin12345678",
            "3. Log in with admin@example.com and password admin12345678",
            "4. Open the 'QA Template' (or create it if missing)",
            "5. Click 'Send' (or 'Create request') to start a new signing request",
            "6. Add two signers: 'Signer One' (signer1@local) and 'Signer Two' (signer2@local)",
            "7. Ensure signing order is sequential (Signer One must complete before Signer Two)",
            "8. Send the request and open the signing link for Signer One",
            "9. Complete all required fields and finish the signature for Signer One",
            "10. Return to the request details and verify Signer Two is now marked as active/pending",
        ],
    },

    # ===== EXCALIDRAW (2 test cases) =====
    {
        "website": "excalidraw",
        "test_name": "Draw Shapes and Edit Text",
        "type": "Canvas drawing - Tests the agent's ability to draw shapes, edit text labels, and reposition elements",
        "instructions": [
            "1. Navigate to http://localhost:8091/",
            "2. Verify the Excalidraw canvas loads",
            "3. Select the Rectangle tool and draw a rectangle on the canvas",
            "4. Select the Text tool and click inside the rectangle",
            "5. Type 'QA Diagram' and click outside to save",
            "6. Drag the rectangle to a new position and verify the text moves with it",
            "7. Select the rectangle and change the stroke color in the style toolbar",
            "8. Verify the rectangle color updates",
        ],
    },
    {
        "website": "excalidraw",
        "test_name": "Export to PNG and Toggle Theme",
        "type": "Export and UI settings - Tests the agent's ability to export the canvas and toggle the UI theme",
        "instructions": [
            "1. Navigate to http://localhost:8091/",
            "2. Draw a simple shape on the canvas (e.g., a circle)",
            "3. Open the Export dialog (or menu) and choose 'Export PNG'",
            "4. Verify a PNG download is triggered",
            "5. Open the theme toggle (Light/Dark) in the UI",
            "6. Switch to the opposite theme and verify the UI changes",
            "7. Switch back to the original theme",
        ],
    },

    # ===== OSRM (2 test cases) =====
    {
        "website": "osrm",
        "test_name": "Route Planning With Detour and Reset",
        "type": "Map navigation and routing - Tests the agent's ability to plan a route, introduce a detour, validate route recalculation, and reset the map state",
        "instructions": [
            "1. Navigate to http://localhost:8092/",
            "2. Verify the OSRM map loads with Start and End search fields and a visible map canvas",
            "3. Enter 'Monaco-Ville' as Start and 'Monte Carlo' as End, then submit",
            "4. Verify a route appears with distance and travel time shown",
            "5. Drag the route line to create a detour via a different street",
            "6. Verify the route recalculates and the distance/time values change",
            "7. Zoom in until street names are readable, then zoom out to view the full route",
            "8. Clear or reset the route using the UI control",
            "9. Verify the map returns to its default state with no route shown",
        ],
    },
    {
        "website": "osrm",
        "test_name": "Swap Directions and Step Focus",
        "type": "Directions panel interaction - Tests the agent's ability to swap route direction, use the turn-by-turn list, and validate map focus",
        "instructions": [
            "1. Navigate to http://localhost:8092/",
            "2. Set Start to 'Fontvieille, Monaco' and End to 'Casino de Monte-Carlo'",
            "3. Verify the route renders and the turn-by-turn list is visible",
            "4. Click the swap/reverse directions control to flip Start and End",
            "5. Verify the route updates and the distance/time values change",
            "6. Click the third turn instruction in the list",
            "7. Verify the map pans/zooms to highlight that segment of the route",
            "8. Click a different instruction and verify the map focus changes again",
            "9. End the route by clearing the inputs or using the reset control",
        ],
    },
]


def init_db():
    """Initialize the SQLite database and populate with benchmark test cases."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website TEXT NOT NULL,
            test_name TEXT NOT NULL,
            type TEXT NOT NULL,
            instructions TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Clear existing data and repopulate
    cursor.execute("DELETE FROM benchmark_tests")

    for tc in BENCHMARK_TEST_CASES:
        instructions_text = "\n".join(tc["instructions"])
        cursor.execute(
            "INSERT INTO benchmark_tests (website, test_name, type, instructions) VALUES (?, ?, ?, ?)",
            (tc["website"], tc["test_name"], tc["type"], instructions_text),
        )

    conn.commit()
    conn.close()


def get_all_tests():
    """Return all benchmark test cases as a list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT website, test_name, type, instructions FROM benchmark_tests ORDER BY id")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def generate_csv() -> str:
    """Generate CSV string with headers: Website, Test Name, Type, Instructions."""
    rows = get_all_tests()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Website", "Test Name", "Type", "Instructions"])
    for row in rows:
        writer.writerow([row["website"], row["test_name"], row["type"], row["instructions"]])
    return output.getvalue()
