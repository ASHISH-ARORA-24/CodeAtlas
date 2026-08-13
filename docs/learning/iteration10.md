ITERATION 10 — MCP

Now take tools we've already built:

search_code()
get_dependencies()
read_file()

and expose them through an MCP server.

Agent / MCP Client
        ↓
       MCP
        ↓
 CodeAtlas MCP Server
        ↓
 ┌──────┼───────────┐
 ↓      ↓           ↓
Search Dependencies Read
 ↓      ↓           ↓
Chroma Neo4j       Repo
Learn

MCP
MCP Host
MCP Client
MCP Server
Tools
Resources
Tool discovery
MCP vs direct function calling

Because we've already built normal tools, we'll actually understand what problem MCP solves.
