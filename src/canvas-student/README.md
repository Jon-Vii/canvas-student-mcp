# Canvas Student MCP

A Model Context Protocol (MCP) integration for interacting with Canvas LMS.

## Setup

### Prerequisites

- Python 3.10 or newer
- [Claude Desktop](https://claude.ai/desktop)
- [UV](https://github.com/astral-sh/uv) Python package manager

### Installation

#### Option 1: Simple Installation (Recommended)

1. Clone this repository 
2. Run the installation script:

```bash
# Navigate to the canvas-student directory
cd src/canvas-student

# Run the installer Python script
python install.py
```

This script will:
- Detect if you have UV or pip available
- Install the package with PDF support
- Provide next steps for configuration

#### Option 2: Manual Installation

1. Clone this repository 
2. Install dependencies:

```bash
# Navigate to the canvas-student directory
cd src/canvas-student

# Install with UV (including PDF support)
uv pip install -e ".[pdf]"

# Or with standard pip
pip install -e ".[pdf]"
```

### Configuration for Claude Desktop

Edit your Claude Desktop configuration file:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add the following configuration:

```json
{
  "mcpServers": {
    "canvas": {
      "command": "python",
      "args": ["ABSOLUTE_PATH_TO/src/canvas-student/main.py"],
      "env": {
        "CANVAS_API_TOKEN": "your_canvas_api_token",
        "CANVAS_BASE_URL": "https://your-institution.instructure.com"
      }
    }
  }
}
```

Replace:
- `ABSOLUTE_PATH_TO` with the absolute path to your project
- `your_canvas_api_token` with your Canvas API token
- `your-institution.instructure.com` with your institution's Canvas URL

> **Note**: The tool now uses Canvas's preview capabilities for files like PDFs, providing URLs for direct access when previews aren't available.

### Troubleshooting

If you encounter issues:

1. Check the Claude Desktop logs:
   - Windows: `%APPDATA%\Claude\logs\mcp-server-canvas.log`
   - macOS: `~/Library/Logs/Claude/mcp-server-canvas.log`

2. Verify the path in your configuration is correct

3. Make sure you're using Python 3.10 or newer

### Authentication Issues

If you encounter authentication problems:

1. **Check your API token**: Make sure your Canvas API token is valid and not expired. You can create a new token from your Canvas account settings under "Approved Integrations".

2. **URL Format**: Ensure your Canvas URL is correctly formatted:
   - Should start with `https://`
   - Should NOT include `/api/v1/`
   - Should NOT have a trailing slash
   - Example: `https://canvas.institution.edu` (correct)
   - Example: `https://canvas.institution.edu/` (incorrect - has trailing slash)

3. **Environment Variables**: If you're getting "CLIENT_ID not configured" errors but are using API token authentication, this is likely because your API token isn't being recognized. Check that your environment variables are correctly set in either:
   - Your `.env` file
   - Your system environment
   - The Claude Desktop configuration

4. **Permissions**: Ensure your Canvas user account has sufficient permissions for the actions you're trying to perform.

## Features

- Retrieve and search courses
- Find and filter assignments
- Access course content (files, modules, pages)
- Search across all Canvas content
- OAuth authentication
- View text file content directly in Claude
- Get links for other file types (PDFs, images, etc.)

## File Content Handling

The Canvas Student MCP tool provides capabilities for handling different file types:

1. **Text Files** (.txt, .md, .csv, .json): Content is displayed directly in Claude
2. **PDFs and Images**: URLs are provided for viewing or downloading these files
3. **Canvas Previews**: When available, Canvas preview content can be shown

This approach doesn't require external libraries and works reliably across all platforms.

Example usage:
```
Show me the content of the assignment description file from course 27849
```

## Configuration

Create a `.env` file with your Canvas credentials:

```
CANVAS_API_TOKEN=your_token_here
CANVAS_BASE_URL=https://your-institution.instructure.com
CANVAS_CLIENT_ID=your_oauth_client_id  # Optional for OAuth
CANVAS_CLIENT_SECRET=your_oauth_client_secret  # Optional for OAuth
REDIRECT_URI=http://localhost:8000/oauth/callback  # Optional for OAuth
```

## Usage

### Running the server directly

For standard usage:
```bash
python canvas_student.py
```

For guaranteed PDF support:
```bash
python run_server.py
```

### Using with Claude for Desktop

1. Find your Claude Desktop configuration file (usually in `~/.config/Claude/claude_desktop_config.json` on macOS/Linux or `%APPDATA%\Claude\claude_desktop_config.json` on Windows)
2. Add this server to your configuration:

```json
{
  "mcpServers": {
    "canvas": {
      "command": "python",
      "args": ["ABSOLUTE_PATH_TO/src/canvas-student/run_server.py"],
      "env": {
        "CANVAS_API_TOKEN": "your_canvas_api_token",
        "CANVAS_BASE_URL": "https://your-institution.instructure.com"
      }
    }
  }
}
```

Replace:
- `ABSOLUTE_PATH_TO` with the absolute path to your project
- `your_canvas_api_token` with your Canvas API token
- `your-institution.instructure.com` with your institution's Canvas URL

> **Note**: The `run_server.py` script automatically ensures PDF extraction libraries are installed before starting the server. This provides a more reliable solution for PDF support.

3. Restart Claude Desktop
4. Look for the MCP icon when chatting with Claude

## Examples

Here are some things you can ask Claude:

- "Show me all my courses"
- "Find exams in my Data Communication course"
- "What assignments are due in the next week?"
- "Search for content about 'machine learning' across all my courses"
- "Extract and show me the content of Lab1P.pdf from course 27849"

### Recent Changes

- **Tool Deprecation**: The `find_course_by_name` tool has been deprecated to reduce redundancy. Use `get_courses` instead and filter the results as needed. This change simplifies the API and improves maintainability.

## Project Structure

- `canvas-student.py`: Main MCP server
- `main.py`: Entry point for the MCP server
- `tools/`: Tools organized by category
  - `courses.py`: Course-related tools
  - `assignments.py`: Assignment-related tools
  - `content.py`: Content/files related tools
  - `search.py`: Search tools
  - `utils.py`: Helper utility tools
  - `file_content.py`: PDF and text content extraction

## License

MIT