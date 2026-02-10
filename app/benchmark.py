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
    # ===== PRESTASHOP (5 test cases) =====
    {
        "website": "prestashop",
        "test_name": "Product Search and Validation",
        "type": "Search functionality - Tests the agent's ability to use a search bar, submit queries, and validate search results against expected product names and prices",
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
        "test_name": "Category Filter by Size and Color",
        "type": "Filtering and faceted navigation - Tests the agent's ability to navigate category menus, apply sidebar filters, verify filtered results, and remove active filters",
        "instructions": [
            "1. Navigate to http://localhost:8086/",
            "2. Click on 'Clothes' in the top navigation menu",
            "3. Verify the Clothes category page loads and the left sidebar shows filter options including Size, Color, and Price",
            "4. Click on the 'Size' filter section and select 'M'",
            "5. Verify the product listing updates and only shows products available in size M",
            "6. Remove the size M filter by clicking the active filter tag or clear button",
            "7. Click on the 'Color' filter section and select 'White'",
            "8. Verify the product listing updates to show only products available in white color",
            "9. Remove the white color filter to show all clothes again",
            "10. Verify all products in the Clothes category are displayed without any active filters",
        ],
    },
    {
        "website": "prestashop",
        "test_name": "Add Product to Cart with Options",
        "type": "E-commerce cart interaction - Tests the agent's ability to select product variants (size, color), adjust quantity, add to cart, and verify the confirmation popup with correct pricing math",
        "instructions": [
            "1. Navigate to http://localhost:8086/",
            "2. Click on 'Hummingbird printed t-shirt' from the Popular Products section",
            "3. Verify the product detail page shows the product name, image, price €19.12, size selector, color selector, and quantity input defaulting to 1",
            "4. Select size 'M' from the size options",
            "5. Set the quantity to 2 using the plus button or quantity input",
            "6. Click the 'Add to Cart' button",
            "7. Verify a confirmation popup appears showing 'Product successfully added to your shopping cart' with quantity 2 and subtotal €38.24",
            "8. Click 'Continue Shopping' to dismiss the popup",
            "9. Verify the cart icon in the header now shows 2 items",
            "10. Verify the page remains on the product detail page after dismissing the popup",
        ],
    },
    {
        "website": "prestashop",
        "test_name": "Multi-Product Cart Verification",
        "type": "Cart management and price validation - Tests the agent's ability to add multiple different products to cart, navigate to cart page, and verify line items, quantities, and total price calculations",
        "instructions": [
            "1. Navigate to http://localhost:8086/men/1-1-hummingbird-printed-t-shirt.html",
            "2. Set quantity to 2 and click 'Add to Cart'",
            "3. Click 'Continue Shopping' to stay on the page",
            "4. Navigate to 'Accessories' in the top menu, then click 'Home Accessories'",
            "5. Click on the 'Mug The best is yet to come' product",
            "6. Leave quantity as 1 and click 'Add to Cart'",
            "7. Verify the cart icon in the header now shows 3 total items",
            "8. Click on the cart icon to go to the cart page",
            "9. Verify the cart page shows two line items: 'Hummingbird printed t-shirt' with quantity 2 and 'Mug The best is yet to come' with quantity 1",
            "10. Verify the overall cart total equals the sum of all line totals (€38.24 + €11.90 = €50.14)",
        ],
    },
    {
        "website": "prestashop",
        "test_name": "Category Navigation and Product Browsing",
        "type": "Navigation and content verification - Tests the agent's ability to navigate through category hierarchy, verify page titles and breadcrumbs, and browse product listings across different categories",
        "instructions": [
            "1. Navigate to http://localhost:8086/",
            "2. Click on 'Clothes' in the top navigation menu",
            "3. Verify the page heading shows 'Clothes' and products are displayed",
            "4. Click on 'Accessories' in the top navigation menu",
            "5. Verify the page heading shows 'Accessories' and subcategories 'Stationery' and 'Home Accessories' are visible",
            "6. Click on 'Home Accessories' subcategory",
            "7. Verify the Home Accessories page loads with mug products listed",
            "8. Click on 'Art' in the top navigation menu",
            "9. Verify the Art category page loads with framed poster products displayed",
            "10. Click the PrestaShop logo to return to the homepage and verify the Popular Products section is visible",
        ],
    },

    # ===== FILEBROWSER (5 test cases) =====
    {
        "website": "filebrowser",
        "test_name": "Login and Folder Management",
        "type": "Authentication and directory operations - Tests the agent's ability to log in with credentials, create folders, navigate into folders using double-click, verify breadcrumbs, and navigate back",
        "instructions": [
            "1. Navigate to http://localhost:8087/",
            "2. Verify the login page loads showing the File Browser logo, username field, password field, and Login button",
            "3. Enter 'admin' in the username field and 'admin12345678' in the password field",
            "4. Click the Login button",
            "5. Verify the file manager dashboard loads showing the toolbar at the top",
            "6. Click the 'New Folder' button in the toolbar",
            "7. Type 'Test Documents' as the folder name in the prompt and confirm",
            "8. Verify the folder 'Test Documents' appears in the file listing",
            "9. Double-click on the 'Test Documents' folder to navigate into it",
            "10. Verify the breadcrumb navigation shows the path includes 'Test Documents' and the directory is empty",
        ],
    },
    {
        "website": "filebrowser",
        "test_name": "File Create Edit and Delete",
        "type": "File CRUD operations - Tests the agent's ability to create new files, use the built-in text editor to add content, save files, verify file sizes, and delete files with confirmation",
        "instructions": [
            "1. Navigate to http://localhost:8087/ and log in with admin/admin12345678",
            "2. Click the 'New File' button in the toolbar",
            "3. Type 'notes.txt' as the file name and confirm",
            "4. Verify the built-in text editor opens for the newly created file",
            "5. Type 'This is a test note for QA verification.' into the editor",
            "6. Click the Save button to save the file content",
            "7. Navigate back to the root directory using the breadcrumb navigation",
            "8. Verify 'notes.txt' is listed with a non-zero file size",
            "9. Select 'notes.txt' by clicking its checkbox and click the Delete button",
            "10. Confirm the deletion and verify 'notes.txt' is removed from the listing",
        ],
    },
    {
        "website": "filebrowser",
        "test_name": "Multi-Select and Bulk Operations",
        "type": "Multi-selection UI interaction - Tests the agent's ability to enable multi-select mode, select multiple files, verify selection count badge, use clear selection, and perform bulk actions",
        "instructions": [
            "1. Navigate to http://localhost:8087/ and log in with admin/admin12345678",
            "2. Create two test files: click 'New File', name it 'file1.txt', confirm, type some text, save, and navigate back to root",
            "3. Repeat to create 'file2.txt' with different content",
            "4. Click the 'Select multiple' (check_circle) button in the toolbar",
            "5. Verify a banner appears at the bottom showing 'Multiple selection enabled'",
            "6. Click on 'file1.txt' and 'file2.txt' to select both files",
            "7. Verify both files are highlighted and the Download button shows a badge with count '2'",
            "8. Click the 'Clear' button in the multi-selection banner at the bottom",
            "9. Verify all files are deselected and no files show the active/selected state",
            "10. Delete both test files to clean up",
        ],
    },
    {
        "website": "filebrowser",
        "test_name": "Editor Font Size and Theme",
        "type": "Settings and editor customization - Tests the agent's ability to change editor font size, navigate to profile settings, change the Ace editor theme, and verify visual changes take effect",
        "instructions": [
            "1. Navigate to http://localhost:8087/ and log in with admin/admin12345678",
            "2. Create a new file named 'fonttest.txt' using the 'New File' button",
            "3. In the text editor that opens, note the font size label displaying '14px'",
            "4. Click the 'Increase font size' (+) button once",
            "5. Verify the font size label now displays '15px'",
            "6. Click the 'Settings' button in the left navigation sidebar",
            "7. Click 'Profile Settings' in the settings sidebar menu",
            "8. Locate the 'Ace editor theme' dropdown and select 'monokai' from the list",
            "9. Click the 'Update' button to save the theme change",
            "10. Navigate back to 'My files', open 'fonttest.txt', and verify the editor uses the monokai dark theme",
        ],
    },
    {
        "website": "filebrowser",
        "test_name": "Single Click Mode and Navigation",
        "type": "User preference toggle and browser navigation - Tests the agent's ability to toggle single-click mode in settings, verify behavior change, and use browser back button for navigation",
        "instructions": [
            "1. Navigate to http://localhost:8087/ and log in with admin/admin12345678",
            "2. Create a test file 'clicktest.txt' with some content and navigate back to root",
            "3. Click 'Settings' in the sidebar, then click 'Profile Settings'",
            "4. Check the checkbox labeled 'Use single clicks to open files and directories'",
            "5. Click the 'Update' button to save",
            "6. Navigate back to 'My files' and single-click on 'clicktest.txt'",
            "7. Verify the file opens directly in the editor (URL changes to /files/clicktest.txt) instead of just selecting it",
            "8. Click 'Settings' in the sidebar, then click 'User Management'",
            "9. Click the browser Back button",
            "10. Verify the URL returns to the previous settings page and correct content is displayed",
        ],
    },

    # ===== FOCALBOARD (5 test cases) =====
    {
        "website": "focalboard",
        "test_name": "Login and Board Creation",
        "type": "Authentication and template usage - Tests the agent's ability to handle failed login, successful login, dismiss notifications, select a template, and verify board creation with correct views",
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
        "test_name": "Card Properties and Status Change",
        "type": "Card detail editing - Tests the agent's ability to open card details, read property values, change status via dropdown, set a date with date picker, toggle checkboxes, and verify changes persist on the board",
        "instructions": [
            "1. Navigate to http://localhost:8088/ and log in with admin/admin12345678",
            "2. Create a board from the 'Project Tasks' template if none exists",
            "3. On the 'Progress Tracker' board view, click the 'Project budget approval' card in the 'Not Started' column",
            "4. Verify the card detail dialog opens showing Status: 'Not Started', Priority: '1. High', Estimated Hours: '16'",
            "5. Click the Status property value 'Not Started' and change it to 'In Progress'",
            "6. Verify the Status now shows 'In Progress'",
            "7. Click the 'Due Date' property showing 'Empty' and select today's date from the date picker",
            "8. Verify the Due Date displays today's date",
            "9. Click the first checkbox in the checklist to mark it as done",
            "10. Close the card detail dialog and verify the card has moved to the 'In Progress' column",
        ],
    },
    {
        "website": "focalboard",
        "test_name": "Search Filter and Sort Cards",
        "type": "Board search, filtering, and sorting - Tests the agent's ability to search for cards by keyword, apply property-based filters, sort by priority, and toggle visible properties on the board",
        "instructions": [
            "1. Navigate to http://localhost:8088/ and log in with admin/admin12345678",
            "2. Open the 'Project Tasks' board and ensure the 'Progress Tracker' view is active",
            "3. Click the search field and type 'budget'",
            "4. Verify only 'Project budget approval' card is visible and other cards are hidden",
            "5. Clear the search field to show all cards again",
            "6. Click the 'Filter' button and add a filter: Priority equals '1. High'",
            "7. Verify only cards with High priority are displayed",
            "8. Remove the filter to show all cards again",
            "9. Click the 'Sort' button and add a sort by 'Priority'",
            "10. Verify cards within columns are reordered based on their Priority values",
        ],
    },
    {
        "website": "focalboard",
        "test_name": "Calendar View Navigation",
        "type": "Calendar UI interaction - Tests the agent's ability to switch views, navigate months using arrows, use the TODAY button, toggle week/month views, and create cards by clicking date cells",
        "instructions": [
            "1. Navigate to http://localhost:8088/ and log in with admin/admin12345678",
            "2. Open the 'Project Tasks' board and click 'Task Calendar' in the sidebar",
            "3. Verify the calendar loads showing 'February 2026' with day headers Sun through Sat",
            "4. Click the right arrow navigation button to go to March 2026",
            "5. Verify the calendar heading changes to 'March 2026'",
            "6. Click the left arrow to return to February 2026",
            "7. Click the right arrow twice to navigate to April 2026",
            "8. Click the 'TODAY' button and verify the calendar returns to February 2026",
            "9. Click the 'Week' button and verify only 7 days for the current week are shown",
            "10. Click the 'Month' button to return to the full month grid view",
        ],
    },
    {
        "website": "focalboard",
        "test_name": "Table View and Settings",
        "type": "Table view data manipulation and settings - Tests the agent's ability to read tabular data, edit cell values, verify calculated sums update, add new rows, access settings menu, and export data",
        "instructions": [
            "1. Navigate to http://localhost:8088/ and log in with admin/admin12345678",
            "2. Open the 'Project Tasks' board and click 'Task Overview' in the sidebar",
            "3. Verify the table view loads with columns: Name, Status, Priority, Date Created, Due Date, Assignee, Created By, Estimated Hours",
            "4. Verify all cards are listed as rows with their property values",
            "5. Verify the bottom calculation row shows 'Count' for Name and 'Sum' for Estimated Hours",
            "6. Click the Estimated Hours cell for 'Identify dependencies' and change the value from 16 to 24",
            "7. Verify the Sum at the bottom updates to reflect the new total",
            "8. Click '+ New' below the last row to add a new empty row",
            "9. Click 'Settings' at the bottom of the sidebar and verify options: Import, Export archive, Set language, Set theme",
            "10. Click 'Export archive' and verify a file download is triggered",
        ],
    },

    # ===== CENTRIFUGO (5 test cases) =====
    {
        "website": "centrifugo",
        "test_name": "Admin Dashboard Status Check",
        "type": "Dashboard verification and status monitoring - Tests the agent's ability to navigate an admin UI, read status cards and tables, verify node information, and confirm server metrics",
        "instructions": [
            "1. Navigate to the Centrifugo admin UI at http://localhost:8089/",
            "2. Verify the admin dashboard loads showing 'Centrifugo' logo, 'Status' tab, 'Actions' tab, and a settings icon",
            "3. Verify the Status page displays three summary cards: 'NODES RUNNING: 1', 'TOTAL CLIENTS: 0', 'TOTAL SUBS: 0'",
            "4. Verify the detailed status table shows columns: Node name, Version, Uptime, Clients, Users, Subs, Channels",
            "5. Verify one row exists showing version '6.6.0 OSS' with all client/channel counts at 0",
            "6. Click the settings icon in the top right corner",
            "7. Verify the Settings page shows 'Enable dark theme' toggle and a reset button",
            "8. Click the 'Enable dark theme' toggle and verify the UI switches to dark theme",
            "9. Click the toggle again to switch back to light theme",
            "10. Click the 'Status' tab and verify the Uptime value has been incrementing",
        ],
    },
    {
        "website": "centrifugo",
        "test_name": "HTTP API Publish and Info",
        "type": "API form interaction - Tests the agent's ability to use a method dropdown, fill form fields, execute API calls, and verify JSON responses for Info, Publish, and Channels methods",
        "instructions": [
            "1. Navigate to http://localhost:8089/ and click the 'Actions' tab",
            "2. Verify the Actions page shows a Method dropdown, Channel field, JSON editor, and a submit button",
            "3. Select 'Info' from the Method dropdown and click the 'Info' button",
            "4. Verify the response shows 'Response OK' with a JSON containing a 'nodes' array with version '6.6.0 OSS'",
            "5. Select 'Publish' from the Method dropdown",
            "6. Enter 'test-channel' in the Channel field and type '{\"message\": \"Hello from test\"}' in the JSON editor",
            "7. Click the 'Publish' button",
            "8. Verify the response shows 'Response OK' with result '{}'",
            "9. Select 'Channels' from the Method dropdown and click 'Channels'",
            "10. Verify the response returns with a 'channels' object in the result",
        ],
    },
    {
        "website": "centrifugo",
        "test_name": "Subscribe Presence and Broadcast",
        "type": "Server-side subscription management - Tests the agent's ability to execute subscribe, presence, broadcast, unsubscribe, and disconnect API commands with required parameters",
        "instructions": [
            "1. Navigate to http://localhost:8089/ and click the 'Actions' tab",
            "2. Select 'Subscribe' from the Method dropdown",
            "3. Enter 'test-user-1' in the User ID field and 'notifications' in the Channel field, then click Subscribe",
            "4. Verify the response shows 'Response OK'",
            "5. Select 'Presence Stats' from the Method dropdown, enter 'notifications' in the Channel field, and click 'Presence Stats'",
            "6. Verify the response returns with 'num_clients' and 'num_users' fields",
            "7. Select 'Broadcast', enter 'channel-a, channel-b' in the Channels field and '{\"event\": \"test\"}' in the JSON editor, then click Broadcast",
            "8. Verify the response shows 'Response OK'",
            "9. Select 'Unsubscribe', enter 'test-user-1' and 'notifications', then click Unsubscribe",
            "10. Verify the response shows 'Response OK' confirming the user was unsubscribed",
        ],
    },
    {
        "website": "centrifugo",
        "test_name": "All API Methods Enumeration",
        "type": "Dropdown enumeration and method verification - Tests the agent's ability to enumerate all available options in a dropdown and verify each API method is accessible",
        "instructions": [
            "1. Navigate to http://localhost:8089/ and click the 'Actions' tab",
            "2. Click the Method dropdown to expand it",
            "3. Verify all methods are listed: Publish, Broadcast, Presence, Presence Stats, History, History Remove, Subscribe, Unsubscribe, Disconnect, Info, RPC, Channels",
            "4. Select 'History' and enter 'test-channel' in Channel field, then click History",
            "5. Verify the response returns (may show error if history not enabled for channel)",
            "6. Select 'History Remove' and enter 'test-channel', then click History Remove",
            "7. Verify the response is processed",
            "8. Select 'Disconnect', enter 'test-user-1' in User ID, and click Disconnect",
            "9. Verify the response shows 'Response OK'",
            "10. Select 'Info' and click Info to verify the node is still running with non-zero API call counts",
        ],
    },
    {
        "website": "centrifugo",
        "test_name": "Dark Theme Toggle and Settings",
        "type": "Theme switching and UI state verification - Tests the agent's ability to access settings, toggle visual themes, verify CSS changes, and reset settings",
        "instructions": [
            "1. Navigate to http://localhost:8089/",
            "2. Verify the default light theme is active (light background)",
            "3. Click the settings icon in the top right corner",
            "4. Verify the Settings page shows 'Enable dark theme' toggle and 'Drop saved settings, tokens and restart' button",
            "5. Click the 'Enable dark theme' toggle switch",
            "6. Verify the UI immediately switches to a dark background color scheme",
            "7. Click the 'Status' tab and verify the dashboard displays correctly in dark theme",
            "8. Click the 'Actions' tab and verify the form elements are visible in dark theme",
            "9. Click the settings icon again and click the 'Enable dark theme' toggle to switch back",
            "10. Verify the UI returns to the default light theme",
        ],
    },

    # ===== CENTRIFUGO CLIENT (5 test cases) =====
    {
        "website": "centrifugo-client",
        "test_name": "WebSocket Connect and Chat",
        "type": "WebSocket real-time messaging - Tests the agent's ability to connect via WebSocket transport, subscribe to channels, send chat messages, and verify real-time message delivery with correct user and timestamp",
        "instructions": [
            "1. Navigate to http://localhost:8085/static/centrifugo-client.html",
            "2. Verify the page loads with title 'Centrifugo Visual Test Client' and status shows 'Disconnected' with a red dot",
            "3. Verify the Transport dropdown is set to 'WebSocket' and Server URL shows 'ws://localhost:8089/connection/websocket'",
            "4. Click the Connect button",
            "5. Verify status changes to 'Connected' with a green dot and status bar shows 'Transport: websocket' with a Client ID",
            "6. Enter 'chat' in the Subscribe panel's Channel field and click Subscribe",
            "7. Verify 'chat' appears under 'Active Subscriptions'",
            "8. Type 'Hello everyone, WebSocket here!' in the chat input and press Enter",
            "9. Verify the message appears in the Messages panel with channel 'chat', username 'tester', and the correct text",
            "10. Click the Disconnect button and verify status returns to 'Disconnected' with a red dot",
        ],
    },
    {
        "website": "centrifugo-client",
        "test_name": "SSE Transport Chat",
        "type": "SSE transport switching and messaging - Tests the agent's ability to switch transport protocols via dropdown, verify URL changes, connect via SSE, send messages, and verify delivery over Server-Sent Events",
        "instructions": [
            "1. Navigate to http://localhost:8085/static/centrifugo-client.html",
            "2. Select 'SSE (Server-Sent Events)' from the Transport dropdown",
            "3. Verify the Server URL changes to 'http://localhost:8089/connection/sse'",
            "4. Click the Connect button",
            "5. Verify status changes to 'Connected' with green dot and Transport shows 'sse'",
            "6. Enter 'chat' in the Channel field and click Subscribe",
            "7. Verify 'chat' appears under 'Active Subscriptions'",
            "8. Type 'Hello from SSE transport!' in the chat input and press Enter",
            "9. Verify the message appears in the Messages panel with username 'tester' and correct text",
            "10. Click Disconnect and verify status returns to 'Disconnected'",
        ],
    },
    {
        "website": "centrifugo-client",
        "test_name": "HTTP-Streaming Transport Chat",
        "type": "HTTP-Streaming transport - Tests the agent's ability to select HTTP-Streaming from transport dropdown, verify URL changes to http_stream endpoint, connect, send messages, and verify delivery",
        "instructions": [
            "1. Navigate to http://localhost:8085/static/centrifugo-client.html",
            "2. Select 'HTTP-Streaming' from the Transport dropdown",
            "3. Verify the Server URL changes to 'http://localhost:8089/connection/http_stream'",
            "4. Click the Connect button",
            "5. Verify status changes to 'Connected' with green dot and Transport shows 'http_stream'",
            "6. Enter 'chat' in the Channel field and click Subscribe",
            "7. Verify 'chat' appears under 'Active Subscriptions'",
            "8. Type 'Hello from HTTP-Streaming!' in the chat input and press Enter",
            "9. Verify the message appears in the Messages panel with username 'tester' and correct text",
            "10. Click Disconnect and verify status returns to 'Disconnected'",
        ],
    },
    {
        "website": "centrifugo-client",
        "test_name": "Server-Side Publish via API Panel",
        "type": "Cross-component interaction - Tests the agent's ability to use the Server HTTP API panel to publish a message from a different user, simulating server-side events, and verify the message appears in the chat",
        "instructions": [
            "1. Navigate to http://localhost:8085/static/centrifugo-client.html",
            "2. Verify Transport is 'WebSocket' and click Connect",
            "3. Subscribe to the 'chat' channel",
            "4. Type 'First message from tester' in chat input and press Enter",
            "5. Verify the message appears in the Messages panel",
            "6. In the Server HTTP API panel on the left, select 'Publish' from the Method dropdown",
            '7. Change the Params JSON to: {"channel": "chat", "data": {"text": "Hey! I joined via the server API.", "user": "admin"}}',
            "8. Click the Execute button",
            "9. Verify a new message appears in the Messages panel with username 'admin' and text 'Hey! I joined via the server API.'",
            "10. Verify both messages are visible in chronological order: one from 'tester' and one from 'admin'",
        ],
    },
    {
        "website": "centrifugo-client",
        "test_name": "Multi-Message Chat Verification",
        "type": "Message ordering and UI panel verification - Tests the agent's ability to send multiple sequential messages, verify chronological ordering, check Connection Log tab, and verify presence panel functionality",
        "instructions": [
            "1. Navigate to http://localhost:8085/static/centrifugo-client.html",
            "2. Click Connect with default WebSocket transport",
            "3. Subscribe to the 'chat' channel",
            "4. Send three messages in sequence: 'Message one', 'Message two', 'Message three'",
            "5. Verify all three messages appear in the Messages panel in chronological order",
            "6. Click the 'Connection Log' tab in the right panel",
            "7. Verify the log shows connection and subscription events",
            "8. Click the 'Presence' tab in the right panel",
            "9. Click the 'Messages' tab to return to the messages view",
            "10. Disconnect and verify all connection state resets (Transport: '-', Client ID: '-')",
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
