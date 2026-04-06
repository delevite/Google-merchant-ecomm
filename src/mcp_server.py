"""
MCP Server Implementation
File: src/mcp_server.py
Purpose: Model Context Protocol server exposing commerce tools to LLMs
Size: ~800 lines

Exposes tools for:
- Product search and browsing
- Inventory checking
- Cart validation
- Checkout session creation
- A2A transaction execution
- Order tracking
- User recommendations
"""

from flask import Blueprint, request, jsonify, current_app
from typing import Dict, List, Any, Tuple, Optional
import uuid
import json
import logging
from datetime import datetime, timedelta

# Initialize logger
logger = logging.getLogger(__name__)

# ============================================================================
# MCP Tool Definitions
# ============================================================================

class MCPToolRegistry:
    """Registry of all tools exposed via MCP protocol."""
    
    def __init__(self):
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register Phase 4 commerce tools."""
        tools = {
            # Search & Browse
            "search_products": {
                "name": "search_products",
                "description": "Search for products by query with filters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "category": {"type": "string", "description": "Optional category filter"},
                        "max_price": {"type": "number", "description": "Maximum price filter"},
                        "min_rating": {"type": "number", "description": "Minimum rating filter"},
                        "limit": {"type": "integer", "description": "Max results (1-50)", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            "browse_category": {
                "name": "browse_category",
                "description": "Browse products in a specific category",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Category path"},
                        "limit": {"type": "integer", "description": "Max results", "default": 20},
                        "sort": {"type": "string", "enum": ["rating", "price_asc", "price_desc", "trending"], "default": "rating"}
                    },
                    "required": ["category"]
                }
            },
            "get_product_details": {
                "name": "get_product_details",
                "description": "Get detailed product information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID or GTIN"}
                    },
                    "required": ["product_id"]
                }
            },
            "check_inventory": {
                "name": "check_inventory",
                "description": "Check real-time inventory status",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of product IDs to check"
                        }
                    },
                    "required": ["product_ids"]
                }
            },
            # Transaction Tools
            "validate_cart": {
                "name": "validate_cart",
                "description": "Validate cart items before checkout",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "string"},
                                    "quantity": {"type": "integer", "minimum": 1}
                                },
                                "required": ["product_id", "quantity"]
                            },
                            "description": "Cart items"
                        }
                    },
                    "required": ["items"]
                }
            },
            "create_checkout_session": {
                "name": "create_checkout_session",
                "description": "Create A2A checkout session",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string", "description": "AI agent identifier"},
                        "user_id": {"type": "string", "description": "End user identifier"},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "string"},
                                    "quantity": {"type": "integer"}
                                }
                            }
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional session metadata (search_query, source, preferences)"
                        }
                    },
                    "required": ["agent_id", "user_id", "items"]
                }
            },
            "execute_a2a_transaction": {
                "name": "execute_a2a_transaction",
                "description": "Execute A2A transaction (payment + order creation)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Checkout session ID"},
                        "payment_method": {"type": "string", "enum": ["paystack", "card", "wallet"]},
                        "metadata": {"type": "object", "description": "Payment metadata"}
                    },
                    "required": ["session_id", "payment_method"]
                }
            },
            "check_order_status": {
                "name": "check_order_status",
                "description": "Check status of A2A order",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "string", "description": "Order ID"}
                    },
                    "required": ["order_id"]
                }
            },
            # User Context
            "get_user_history": {
                "name": "get_user_history",
                "description": "Get user's purchase history and preferences",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID"},
                        "limit": {"type": "integer", "description": "Max orders to return", "default": 10}
                    },
                    "required": ["user_id"]
                }
            },
            "get_recommendations": {
                "name": "get_recommendations",
                "description": "Get AI-powered product recommendations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "User ID"},
                        "limit": {"type": "integer", "description": "Number of recommendations", "default": 5},
                        "context": {"type": "object", "description": "Additional context (category, budget)"}
                    },
                    "required": ["user_id"]
                }
            }
        }
        self.tools = tools
    
    def get_tools(self) -> Dict[str, Any]:
        """Return all available tools."""
        return self.tools
    
    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get specific tool definition."""
        return self.tools.get(tool_name)


class MCPToolExecutor:
    """Execute MCP tools and return results."""
    
    def __init__(self, app_context):
        self.app = app_context
        self.merchant_client = getattr(app_context, '_merchant_client', None)
        self.logger = logging.getLogger(__name__)
    
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return result."""
        try:
            if not hasattr(self, tool_name):
                return {
                    "error": f"Tool '{tool_name}' not found",
                    "code": "TOOL_NOT_FOUND"
                }
            
            method = getattr(self, tool_name)
            result = method(**params)
            return {"success": True, "data": result}
        
        except TypeError as e:
            return {"error": f"Invalid parameters: {str(e)}", "code": "INVALID_PARAMS"}
        except Exception as e:
            self.logger.error(f"Tool execution error: {tool_name}: {str(e)}")
            return {"error": str(e), "code": "EXECUTION_ERROR"}
    
    # ========================================================================
    # Search & Browse Tools
    # ========================================================================
    
    def search_products(self, query: str, category: str = None, 
                       max_price: float = None, min_rating: float = None,
                       limit: int = 10) -> Dict[str, Any]:
        """Search for products."""
        results = {
            "query": query,
            "results_count": 0,
            "products": [],
            "filters_applied": {
                "category": category,
                "max_price": max_price,
                "min_rating": min_rating
            }
        }
        
        # Simulated data - replace with real search in Phase 4 implementation
        if query.lower() in ["dog supplies", "cat toys", "pet accessories", "pet products"]:
            results["results_count"] = 25
            results["products"] = [
                {
                    "product_id": f"prod-{i}",
                    "title": f"{query} product {i}",
                    "price": 19.99 + (i * 5),
                    "rating": 4.5 + (i * 0.1),
                    "in_stock": True,
                    "category": category or "Pet Supplies"
                }
                for i in range(min(limit, 5))
            ]
        
        return results
    
    def browse_category(self, category: str, limit: int = 20,
                       sort: str = "rating") -> Dict[str, Any]:
        """Browse category."""
        return {
            "category": category,
            "sort": sort,
            "products": [],
            "total_count": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_product_details(self, product_id: str) -> Dict[str, Any]:
        """Get product details."""
        return {
            "product_id": product_id,
            "title": f"Product {product_id}",
            "description": "Product details will be fetched from Phase 3 API",
            "price": 29.99,
            "rating": 4.5,
            "reviews_count": 120,
            "in_stock": True,
            "sku": f"SKU-{product_id}",
            "gtin": f"GTIN-{product_id}"
        }
    
    def check_inventory(self, product_ids: List[str]) -> Dict[str, Any]:
        """Check real-time inventory."""
        inventory = {
            "timestamp": datetime.utcnow().isoformat(),
            "products": {}
        }
        
        for product_id in product_ids:
            inventory["products"][product_id] = {
                "in_stock": True,
                "quantity": 50 + (hash(product_id) % 100),
                "last_updated": datetime.utcnow().isoformat()
            }
        
        return inventory
    
    # ========================================================================
    # Transaction Tools
    # ========================================================================
    
    def validate_cart(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate cart before checkout."""
        validation = {
            "valid": True,
            "items_validated": len(items),
            "total_price": 0,
            "issues": []
        }
        
        for item in items:
            if item['quantity'] <= 0:
                validation["issues"].append(f"Invalid quantity for {item['product_id']}")
                validation["valid"] = False
            
            validation["total_price"] += 29.99 * item['quantity']
        
        return validation
    
    def create_checkout_session(self, agent_id: str, user_id: str,
                               items: List[Dict[str, Any]],
                               metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create A2A checkout session."""
        session_id = str(uuid.uuid4())
        
        session = {
            "session_id": session_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "status": "active",
            "items": items,
            "metadata": metadata or {},
            "items_count": sum(item['quantity'] for item in items),
            "estimated_total": sum(29.99 * item['quantity'] for item in items)
        }
        
        logger.info(f"Checkout session created: {session_id}")
        
        return session
    
    def execute_a2a_transaction(self, session_id: str, payment_method: str,
                               metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute A2A transaction."""
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        transaction = {
            "order_id": order_id,
            "session_id": session_id,
            "payment_method": payment_method,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        logger.info(f"A2A transaction initiated: {order_id}")
        
        return transaction
    
    def check_order_status(self, order_id: str) -> Dict[str, Any]:
        """Check A2A order status."""
        return {
            "order_id": order_id,
            "status": "processing",
            "items": [],
            "total": 0,
            "tracking": None,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    # ========================================================================
    # User Context Tools
    # ========================================================================
    
    def get_user_history(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Get user purchase history."""
        return {
            "user_id": user_id,
            "orders": [],
            "total_spent": 0,
            "lifetime_value": 0,
            "last_order": None
        }
    
    def get_recommendations(self, user_id: str, limit: int = 5,
                           context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get product recommendations."""
        return {
            "user_id": user_id,
            "recommendations": [],
            "confidence_scores": [],
            "reason": "Based on purchase history",
            "context": context or {}
        }


# ============================================================================
# MCP Blueprint & Routes
# ============================================================================

mcp_bp = Blueprint('mcp', __name__, url_prefix='/api/mcp')

@mcp_bp.before_app_request
def init_mcp():
    """Initialize MCP components on app startup."""
    if not hasattr(current_app, '_mcp_registry'):
        current_app._mcp_registry = MCPToolRegistry()
        current_app._mcp_executor = MCPToolExecutor(current_app)


@mcp_bp.route('/tools', methods=['GET'])
def list_tools():
    """List all available MCP tools."""
    registry = current_app._mcp_registry
    return jsonify({
        "tools": list(registry.get_tools().values()),
        "count": len(registry.get_tools()),
        "mcp_version": "1.0"
    }), 200


@mcp_bp.route('/tools/<tool_name>', methods=['GET'])
def get_tool(tool_name):
    """Get specific tool definition."""
    tool = current_app._mcp_registry.get_tool(tool_name)
    if not tool:
        return jsonify({"error": "Tool not found"}), 404
    return jsonify(tool), 200


@mcp_bp.route('/execute', methods=['POST'])
def execute_tool():
    """Execute an MCP tool with JSON-RPC format."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body required"}), 400
    
    tool_name = data.get('tool')
    params = data.get('params', {})
    
    if not tool_name:
        return jsonify({"error": "Tool name required"}), 400
    
    executor = current_app._mcp_executor
    result = executor.execute(tool_name, params)
    
    return jsonify(result), 200


@mcp_bp.route('/status', methods=['GET'])
def mcp_status():
    """Get MCP server status."""
    return jsonify({
        "status": "active",
        "version": "1.0",
        "tools_count": len(current_app._mcp_registry.get_tools()),
        "timestamp": datetime.utcnow().isoformat()
    }), 200
