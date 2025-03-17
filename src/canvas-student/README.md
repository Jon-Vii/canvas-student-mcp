# Canvas Student MCP

A Model Context Protocol (MCP) integration for interacting with Canvas LMS.

## Setup

### Prerequisites

- Python 3.10 or newer
- [Claude Desktop](https://claude.ai/desktop)
- [UV](https://github.com/astral-sh/uv) Python package manager

### Installation

1. Clone this repository 
2. Install dependencies:

```bash
# Navigate to the canvas-student directory
cd src/canvas-student

# Install dependencies with UV
uv pip install -r requirements.txt
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
      "command": "uv",
      "args": [
        "run",
        "ABSOLUTE_PATH_TO/src/canvas-student/main.py"
      ],
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

### Troubleshooting

If you encounter issues:

1. Check the Claude Desktop logs:
   - Windows: `%APPDATA%\Claude\logs\mcp-server-canvas.log`
   - macOS: `~/Library/Logs/Claude/mcp-server-canvas.log`

2. Verify the path in your configuration is correct

3. Make sure you're using Python 3.10 or newer

## Features

- Retrieve and search courses
- Find and filter assignments
- Access course content (files, modules, pages)
- Search across all Canvas content
- OAuth authentication

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

```bash
python canvas-student.py
```

### Using with Claude for Desktop

1. Find your Claude Desktop configuration file (usually in `~/.config/Claude/claude_desktop_config.json` on macOS/Linux or `%APPDATA%\Claude\claude_desktop_config.json` on Windows)
2. Add this server to your configuration:

```json
{
  "mcpServers": {
    "canvas": {
      "command": "python",
      "args": ["/path/to/canvas-student.py"],
      "cwd": "/path/to/canvas-student"
    }
  }
}
```

3. Restart Claude Desktop
4. Look for the MCP icon when chatting with Claude

## Examples

Here are some things you can ask Claude:

- "Show me all my courses"
- "Find exams in my Data Communication course"
- "What assignments are due in the next week?"
- "Search for content about 'machine learning' across all my courses"

## Project Structure

- `canvas-student.py`: Main MCP server
- `tools/`: Tools organized by category
  - `courses.py`: Course-related tools
  - `assignments.py`: Assignment-related tools
  - `content.py`: Content/files related tools
  - `search.py`: Search tools
  - `utils.py`: Helper utility tools

## License

MIT
