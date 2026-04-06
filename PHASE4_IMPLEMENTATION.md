# Phase 4: Native Checkout & AI Agent Support
## MCP Server, A2A Framework, and Conversion Tracking

**Phase 4 Objective**: Achieve **100% UCP Readiness** by enabling AI-driven commerce through:
- **MCP Server** - Model Context Protocol for LLM tool integration
- **A2A Framework** - Agent-to-Agent transaction protocol
- **Native Checkout** - Direct-from-search purchase flow
- **Conversion Tracking** - Attribution and analytics

**Target**: Additional ~15% UCP Readiness (85% → 100%)  
**Estimated Implementation**: 3 days  
**Complexity**: High (event-driven, async, multi-service orchestration)

---

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [MCP Server Implementation](#mcp-server-implementation)
3. [A2A Transaction Framework](#a2a-transaction-framework)
4. [Native Checkout Integration](#native-checkout-integration)
5. [Conversion Tracking & Analytics](#conversion-tracking--analytics)
6. [Implementation Steps](#implementation-steps)
7. [Testing & Deployment](#testing--deployment)
8. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Phase 4 System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM / AI Agent Layer                      │
│              (Claude, GPT-4, Gemini, etc.)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ MCP Protocol
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           MCP Server (src/mcp_server.py)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Search & Browse Tools                                │   │
│  │  - search_products(query, filters)                   │   │
│  │  - browse_category(category)                         │   │
│  │  - get_product_details(product_id)                   │   │
│  │  - check_inventory(product_ids)                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Transaction Tools                                    │   │
│  │  - validate_cart(items)                              │   │
│  │  - create_checkout_session(user_id, items)           │   │
│  │  - execute_a2a_transaction(session_id)               │   │
│  │  - check_order_status(order_id)                      │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ User Context Tools                                   │   │
│  │  - get_user_history(user_id)                         │   │
│  │  - get_user_preferences(user_id)                     │   │
│  │  - get_recommendations(user_id)                      │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
    ┌────────┐  ┌────────┐  ┌──────────┐
    │ Phase1 │  │ Phase 2│  │ Phase 3  │
    │ Auth & │  │ Feed   │  │ Merchant │
    │ Data   │  │ Mgmt   │  │ API      │
    └────────┘  └────────┘  └──────────┘
        │            │            │
        └────────────┼────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ┌─────────────┐      ┌──────────────┐
    │ A2A Router  │      │ Conversion   │
    │ (Protocol & │      │ Tracker      │
    │ Orchestr.)  │      │ (Analytics)  │
    └──────┬──────┘      └──────────────┘
           │
    ┌──────┴──────────┐
    │                 │
    ▼                 ▼
┌──────────────┐  ┌─────────────────┐
│ Payment API  │  │ Order Mgmt      │
│ (Paystack)   │  │ System          │
└──────────────┘  └─────────────────┘
```

### Key Concepts

**1. MCP Server (Model Context Protocol)**
- Exposes tools to LLMs via standardized interface
- Enables AI agents to browse products, manage carts, execute transactions
- Runs as separate service or Flask extension
- Implements: Search, Browse, Cart, Checkout, Order Status, Recommendations

**2. A2A Framework (Agent-to-Agent)**
- Protocol for secure transactions between AI agents and commerce system
- Handles: Identity verification, intent validation, transaction approval
- Prevents: Unauthorized transactions, infinite loops, abuse
- Implements: Session management, approval workflows, dispute resolution

**3. Native Checkout**
- Direct payment flow without user interface
- AI agent submits complete checkout request
- System validates, processes payment, returns order confirmation
- Reduces friction: Browse → Select → PayMetadata → Order (4 steps)

**4. Conversion Tracking**
- Attribute sales to:
  - Source AI agent version
  - Search queries used
  - Recommendation source
  - User preferences matched
- Feedback loop: Track what works, optimize recommendations

---

## MCP Server Implementation

### Component 1: MCP Server Core (src/mcp_server.py)

```python
# File: src/mcp_server.py
# Purpose: MCP server exposing commerce tools to LLMs
# Size: ~800 lines
# Dependencies: flask, json-rpc, google-cloud-merchant, paystack

from flask import Blueprint, request, jsonify, current_app
from typing import Dict, List, Any, Tuple, Optional
import uuid
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
import time

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
        # TODO: Integrate with Merchant API / search service
        # For now, return simulated results
        
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
        if query.lower() in ["dog supplies", "cat toys", "pet accessories"]:
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
        # TODO: Fetch from Merchant API phase 3
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
        # TODO: Integrate with Phase 3 Merchant API
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
            
            # Simulate price lookup
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
        
        # TODO: Save session to database
        
        return session
    
    def execute_a2a_transaction(self, session_id: str, payment_method: str,
                               metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute A2A transaction."""
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        transaction = {
            "order_id": order_id,
            "session_id": session_id,
            "payment_method": payment_method,
            "status": "pending",  # Moves to 'completed' after payment
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # TODO: Process payment via Paystack API
        # TODO: Create order in order management system
        
        return transaction
    
    def check_order_status(self, order_id: str) -> Dict[str, Any]:
        """Check A2A order status."""
        return {
            "order_id": order_id,
            "status": "processing",  # pending, processing, shipped, delivered, cancelled
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
```

### Component 2: Integration with Flask (api.py)

Add MCP Blueprint to main Flask app (in `netlify/functions/api/api.py`):

```python
# In api.py at top of file:
from src.mcp_server import mcp_bp

# After creating app:
app.register_blueprint(mcp_bp)
```

---

## A2A Transaction Framework

### Component: A2A Router (src/a2a_router.py)

```python
# File: src/a2a_router.py
# Purpose: Agent-to-Agent transaction orchestration and protocol
# Size: ~600 lines

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
    """A2A Transaction lifecycle states."""
    INITIATED = "initiated"
    VALIDATED = "validated"
    APPROVED = "approved"
    PAYMENT_PROCESSING = "payment_processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPUTED = "disputed"


class A2ARouter:
    """Route and orchestrate Agent-to-Agent transactions."""
    
    def __init__(self, merchant_client=None, payment_client=None):
        self.merchant_client = merchant_client
        self.payment_client = payment_client
        self.transactions: Dict[str, Dict] = {}  # TODO: Move to persistent storage
        self.logger = logging.getLogger(__name__)
    
    def initiate_transaction(self, agent_id: str, user_id: str,
                            items: List[Dict[str, Any]],
                            metadata: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Initiate A2A transaction.
        
        Returns: (success, transaction_dict)
        """
        transaction_id = f"A2A-{uuid.uuid4().hex[:12].upper()}"
        
        transaction = {
            "transaction_id": transaction_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "status": TransactionStatus.INITIATED.value,
            "created_at": datetime.utcnow().isoformat(),
            "items": items,
            "metadata": metadata or {},
            "validation": None,
            "approval": None,
            "payment": None,
            "order": None
        }
        
        self.transactions[transaction_id] = transaction
        
        self.logger.info(f"Initiated transaction: {transaction_id} | Agent: {agent_id}")
        
        return True, transaction
    
    def validate_transaction(self, transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate transaction (inventory, pricing, user).
        
        Returns: (is_valid, validation_result)
        """
        if transaction_id not in self.transactions:
            return False, {"error": "Transaction not found"}
        
        transaction = self.transactions[transaction_id]
        
        # Validation checks
        validation_result = {
            "transaction_id": transaction_id,
            "inventory_check": True,  # TODO: Check with Phase 3 Merchant API
            "pricing_check": True,    # Verify prices haven't changed
            "user_check": True,       # Verify user is legitimate
            "cart_validity": True,    # Verify items are still available
            "is_valid": True,
            "issues": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Mark as validated
        if validation_result["is_valid"]:
            transaction["status"] = TransactionStatus.VALIDATED.value
            transaction["validation"] = validation_result
            self.logger.info(f"Validated transaction: {transaction_id}")
        else:
            transaction["status"] = TransactionStatus.FAILED.value
            self.logger.warning(f"Validation failed: {transaction_id}")
        
        return validation_result["is_valid"], validation_result
    
    def approve_transaction(self, transaction_id: str,
                           approval_reason: str = "A2A checkout") -> Tuple[bool, Dict[str, Any]]:
        """
        Get approval for high-value transaction or fraud detection triggers.
        
        Returns: (approved, approval_result)
        """
        if transaction_id not in self.transactions:
            return False, {"error": "Transaction not found"}
        
        transaction = self.transactions[transaction_id]
        
        # Calculate transaction risk score
        risk_score = self._calculate_risk_score(transaction)
        
        approval_result = {
            "transaction_id": transaction_id,
            "approved": True,  # TODO: Integrate with approval workflow
            "risk_score": risk_score,
            "needs_review": risk_score > 70,
            "approval_reason": approval_reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if approval_result["approved"]:
            transaction["status"] = TransactionStatus.APPROVED.value
            transaction["approval"] = approval_result
            self.logger.info(f"Approved transaction: {transaction_id}")
        
        return approval_result["approved"], approval_result
    
    def process_payment(self, transaction_id: str, payment_method: str,
                       payment_details: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Process payment via payment processor.
        
        Returns: (success, payment_result)
        """
        if transaction_id not in self.transactions:
            return False, {"error": "Transaction not found"}
        
        transaction = self.transactions[transaction_id]
        
        try:
            # TODO: Integrate with real payment processor (Paystack)
            payment_result = {
                "transaction_id": transaction_id,
                "payment_method": payment_method,
                "amount": sum(item['quantity'] * 29.99 for item in transaction['items']),
                "currency": "NGN",  # Or based on user location
                "status": "completed",  # pending, processing, completed, failed
                "reference": f"PAY-{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            transaction["status"] = TransactionStatus.PAYMENT_PROCESSING.value
            transaction["payment"] = payment_result
            
            self.logger.info(f"Payment processed: {transaction_id} | Ref: {payment_result['reference']}")
            
            return True, payment_result
        
        except Exception as e:
            self.logger.error(f"Payment processing failed: {transaction_id}: {str(e)}")
            transaction["status"] = TransactionStatus.FAILED.value
            return False, {"error": str(e)}
    
    def create_order(self, transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Create order after successful payment.
        
        Returns: (success, order_result)
        """
        if transaction_id not in self.transactions:
            return False, {"error": "Transaction not found"}
        
        transaction = self.transactions[transaction_id]
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        order_result = {
            "order_id": order_id,
            "transaction_id": transaction_id,
            "user_id": transaction['user_id'],
            "agent_id": transaction['agent_id'],
            "items": transaction['items'],
            "total": sum(item['quantity'] * 29.99 for item in transaction['items']),
            "status": "pending_fulfillment",
            "created_at": datetime.utcnow().isoformat(),
            "estimated_delivery": (datetime.utcnow() + timedelta(days=3)).isoformat()
        }
        
        transaction["status"] = TransactionStatus.COMPLETED.value
        transaction["order"] = order_result
        
        # TODO: Save order to order management system
        # TODO: Trigger fulfillment workflow
        
        self.logger.info(f"Order created: {order_id}")
        
        return True, order_result
    
    def _calculate_risk_score(self, transaction: Dict[str, Any]) -> float:
        """Calculate transaction risk score (0-100)."""
        risk_score = 0.0
        
        # TODO: Implement comprehensive risk scoring
        # Factors: high value, new user, atypical pattern, conflicting data, etc.
        
        return risk_score
    
    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction details."""
        return self.transactions.get(transaction_id)
    
    def list_transactions(self, user_id: str = None, agent_id: str = None,
                         limit: int = 50) -> List[Dict[str, Any]]:
        """List transactions with optional filtering."""
        transactions = list(self.transactions.values())
        
        if user_id:
            transactions = [t for t in transactions if t['user_id'] == user_id]
        
        if agent_id:
            transactions = [t for t in transactions if t['agent_id'] == agent_id]
        
        return transactions[-limit:]
```

---

## Native Checkout Integration

### Component: Checkout Service (src/checkout_service.py)

```python
# File: src/checkout_service.py
# Purpose: Native checkout orchestration
# Size: ~400 lines

from typing import Dict, Any, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CheckoutService:
    """Orchestrate complete checkout flow for A2A transactions."""
    
    def __init__(self, a2a_router, merchant_client=None):
        self.a2a_router = a2a_router
        self.merchant_client = merchant_client
    
    def native_checkout(self, agent_id: str, user_id: str,
                       items: List[Dict[str, Any]],
                       payment_method: str = "paystack",
                       metadata: Dict[str, Any] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute complete native checkout flow in one call.
        
        Steps:
        1. Initiate transaction
        2. Validate inventory and pricing
        3. Approve transaction (if needed)
        4. Process payment
        5. Create order
        
        Returns: (success, result)
        """
        
        try:
            # Step 1: Initiate
            logger.info(f"[CHECKOUT] Initiating | Agent: {agent_id} | User: {user_id} | Items: {len(items)}")
            success, transaction = self.a2a_router.initiate_transaction(
                agent_id, user_id, items, metadata
            )
            if not success:
                return False, transaction
            
            transaction_id = transaction['transaction_id']
            
            # Step 2: Validate
            logger.info(f"[CHECKOUT] Validating | Transaction: {transaction_id}")
            is_valid, validation = self.a2a_router.validate_transaction(transaction_id)
            if not is_valid:
                return False, {"error": "Validation failed", "details": validation}
            
            # Step 3: Approve (optional, based on risk)
            logger.info(f"[CHECKOUT] Approving | Transaction: {transaction_id}")
            approved, approval = self.a2a_router.approve_transaction(transaction_id)
            if not approved:
                return False, {"error": "Transaction not approved"}
            
            # Step 4: Process Payment
            payment_details = {
                # TODO: Extract payment details from metadata
            }
            logger.info(f"[CHECKOUT] Processing payment | Transaction: {transaction_id}")
            pay_success, payment = self.a2a_router.process_payment(
                transaction_id, payment_method, payment_details
            )
            if not pay_success:
                return False, {"error": "Payment failed", "details": payment}
            
            # Step 5: Create Order
            logger.info(f"[CHECKOUT] Creating order | Transaction: {transaction_id}")
            order_success, order = self.a2a_router.create_order(transaction_id)
            if not order_success:
                return False, {"error": "Order creation failed"}
            
            logger.info(f"[CHECKOUT] SUCCESS | Order: {order['order_id']} | Transaction: {transaction_id}")
            
            return True, {
                "success": True,
                "order_id": order['order_id'],
                "transaction_id": transaction_id,
                "total": order['total'],
                "estimated_delivery": order['estimated_delivery']
            }
        
        except Exception as e:
            logger.error(f"[CHECKOUT] ERROR: {str(e)}")
            return False, {"error": str(e)}
```

---

## Conversion Tracking & Analytics

### Component: Conversion Tracker (src/conversion_tracker.py)

```python
# File: src/conversion_tracker.py
# Purpose: Attribution and conversion tracking
# Size: ~500 lines

from typing import Dict, Any, List
from datetime import datetime
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class ConversionEvent(Enum):
    """Types of conversion events."""
    PAGE_VIEW = "page_view"
    PRODUCT_VIEW = "product_view"
    ADD_TO_CART = "add_to_cart"
    CHECKOUT_START = "checkout_start"
    CHECKOUT_COMPLETE = "checkout_complete"
    PURCHASE = "purchase"
    AGENT_SESSION_START = "agent_session_start"
    AGENT_SESSION_END = "agent_session_end"
    RECOMMENDATION_SHOWN = "recommendation_shown"
    RECOMMENDATION_CLICKED = "recommendation_clicked"


class ConversionTracker:
    """Track and attribute conversions to AI agents and sources."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []  # TODO: Move to database
        self.sessions: Dict[str, Dict[str, Any]] = {}  # TODO: Move to database
    
    def start_session(self, agent_id: str, user_id: str,
                     context: Dict[str, Any] = None) -> str:
        """Start tracking user session from AI agent."""
        session_id = f"SES-{uuid.uuid4().hex[:12]}"
        
        session = {
            "session_id": session_id,
            "agent_id": agent_id,
            "user_id": user_id,
            "started_at": datetime.utcnow().isoformat(),
            "events": [],
            "context": context or {},
            "converted": False,
            "order_id": None
        }
        
        self.sessions[session_id] = session
        
        self.track_event(
            session_id, ConversionEvent.AGENT_SESSION_START,
            {"agent_id": agent_id}
        )
        
        logger.info(f"Session started: {session_id} | Agent: {agent_id}")
        
        return session_id
    
    def track_event(self, session_id: str, event_type: ConversionEvent,
                   data: Dict[str, Any] = None) -> None:
        """Track conversion event."""
        event = {
            "event_id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": event_type.value,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self.events.append(event)
        
        if session_id in self.sessions:
            self.sessions[session_id]['events'].append(event['event_id'])
        
        logger.debug(f"Event tracked: {event_type.value} | Session: {session_id}")
    
    def track_conversion(self, session_id: str, order_id: str,
                        order_value: float, items_count: int) -> None:
        """Track successful conversion (purchase)."""
        self.track_event(session_id, ConversionEvent.PURCHASE, {
            "order_id": order_id,
            "value": order_value,
            "items": items_count
        })
        
        if session_id in self.sessions:
            self.sessions[session_id]['converted'] = True
            self.sessions[session_id]['order_id'] = order_id
        
        logger.info(f"Conversion tracked: {order_id} | Value: {order_value} | Session: {session_id}")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        session = self.sessions[session_id]
        session_events = [e for e in self.events if e['session_id'] == session_id]
        
        stats = {
            "session_id": session_id,
            "agent_id": session['agent_id'],
            "user_id": session['user_id'],
            "duration_seconds": (
                datetime.fromisoformat(session_events[-1]['timestamp']) 
                - datetime.fromisoformat(session_events[0]['timestamp'])
            ).total_seconds() if session_events else 0,
            "event_count": len(session_events),
            "converted": session['converted'],
            "order_id": session['order_id']
        }
        
        return stats
    
    def get_agent_metrics(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
        """Get metrics for a specific AI agent."""
        # Filter sessions for this agent in the last N days
        agent_sessions = [
            s for s in self.sessions.values()
            if s['agent_id'] == agent_id
        ]
        
        conversions = sum(1 for s in agent_sessions if s['converted'])
        
        metrics = {
            "agent_id": agent_id,
            "period_days": days,
            "sessions": len(agent_sessions),
            "conversions": conversions,
            "conversion_rate": conversions / len(agent_sessions) if agent_sessions else 0,
            "total_revenue": 0,  # TODO: Calculate from converted orders
            "avg_order_value": 0,  # TODO: Calculate
            "events": len([e for e in self.events if any(
                s['agent_id'] == agent_id for s in [self.sessions.get(e['session_id'])]
            )])
        }
        
        return metrics
```

---

## Implementation Steps

### Step 1: Create Phase 4 Module Files
```bash
# Create new files
touch src/mcp_server.py
touch src/a2a_router.py
touch src/checkout_service.py
touch src/conversion_tracker.py
```

### Step 2: Update requirements.txt
Add Phase 4 dependencies:
```
google-cloud-merchant>=0.1.0
schedule>=1.2.0
paystack-sdk>=0.2.0  # For payment processing
python-json-logger>=2.0.0  # For structured logging
```

### Step 3: Update Flask App (api.py)
Register MCP Blueprint and initialize Phase 4 components:
```python
from src.mcp_server import mcp_bp
from src.a2a_router import A2ARouter
from src.checkout_service import CheckoutService
from src.conversion_tracker import ConversionTracker

# Initialize Phase 4 components
_a2a_router = None
_checkout_service = None
_conversion_tracker = None

def init_phase4():
    global _a2a_router, _checkout_service, _conversion_tracker
    _a2a_router = A2ARouter(merchant_client=_merchant_client)
    _checkout_service = CheckoutService(_a2a_router, merchant_client=_merchant_client)
    _conversion_tracker = ConversionTracker()

# Register MCP Blueprint
app.register_blueprint(mcp_bp)

# Initialize on startup
with app.app_context():
    init_phase4()
```

### Step 4: Add Phase 4 Endpoints
Add Flask endpoints for direct checkout, session tracking, and metrics:
```python
@app.route('/api/native-checkout', methods=['POST'])
def native_checkout():
    """Direct A2A checkout endpoint."""
    data = request.get_json()
    
    success, result = _checkout_service.native_checkout(
        data['agent_id'],
        data['user_id'],
        data['items'],
        data.get('payment_method', 'paystack'),
        data.get('metadata')
    )
    
    if success:
        # Track conversion
        _conversion_tracker.track_conversion(
            data.get('session_id'),
            result['order_id'],
            result['total'],
            len(data['items'])
        )
    
    return jsonify(result), 200 if success else 400

@app.route('/api/conversion/session/<session_id>', methods=['GET'])
def get_session_stats(session_id):
    """Get session conversion statistics."""
    stats = _conversion_tracker.get_session_stats(session_id)
    return jsonify(stats), 200

@app.route('/api/conversion/agent/<agent_id>/metrics', methods=['GET'])
def get_agent_metrics(agent_id):
    """Get AI agent performance metrics."""
    days = request.args.get('days', 30, type=int)
    metrics = _conversion_tracker.get_agent_metrics(agent_id, days)
    return jsonify(metrics), 200
```

---

## Testing & Deployment

### Test MCP Server
```bash
# List available tools
curl http://localhost:5000/api/mcp/tools | jq '.'

# Execute search tool
curl -X POST http://localhost:5000/api/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "search_products",
    "params": {
      "query": "dog supplies",
      "limit": 5
    }
  }' | jq '.'

# Execute checkout tool
curl -X POST http://localhost:5000/api/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "create_checkout_session",
    "params": {
      "agent_id": "agent-123",
      "user_id": "user-456",
      "items": [{"product_id": "prod-1", "quantity": 2}]
    }
  }' | jq '.'
```

### Test A2A Transaction Flow
```bash
# Initiate checkout
curl -X POST http://localhost:5000/api/native-checkout \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-123",
    "user_id": "user-456",
    "items": [{"product_id": "prod-1", "quantity": 2}],
    "payment_method": "paystack",
    "session_id": "ses-789"
  }' | jq '.'
```

### Monitor Conversion Metrics
```bash
# Get agent performance
curl http://localhost:5000/api/conversion/agent/agent-123/metrics?days=30 | jq '.'
```

---

## Troubleshooting

### Issue: MCP tools not visible
**Solution**: Verify mcp_bp is registered and MCP components initialized

### Issue: Checkout fails during validation
**Solution**: Check Phase 3 Merchant API connectivity and inventory service

### Issue: Payment processing fails
**Solution**: Verify Paystack API credentials in `.env` and payment method valid

### Issue: Conversion tracking shows zero conversions
**Solution**: Ensure `track_conversion()` called after successful payment and order creation

---

## Success Metrics

**Phase 4 Complete When**:
- ✅ MCP server lists 8+ tools via `/api/mcp/tools`
- ✅ Native checkout completes end-to-end in <5 seconds
- ✅ Conversion dashboard shows agent metrics
- ✅ A2A transactions tracked with proper attribution
- ✅ Risk scoring working for high-value orders
- ✅ All Phase 1-3 features still functional (backwards compatible)

**UCP Readiness**: ~100% (all phases complete)

---

## Next Steps

1. **Implement MCP Server** (Day 1)
   - Create src/mcp_server.py with all tool definitions
   - Register MCP blueprint in Flask app
   - Test tool listing and execution

2. **Implement A2A Router** (Day 2)
   - Create src/a2a_router.py with transaction orchestration
   - Implement validation, approval, payment workflows
   - Test end-to-end transaction flow

3. **Integrate Native Checkout** (Day 2-3)
   - Create src/checkout_service.py
   - Add /api/native-checkout endpoint
   - Test from agent perspective

4. **Add Conversion Tracking** (Day 3)
   - Create src/conversion_tracker.py
   - Add session and event tracking
   - Build agent metrics dashboard

5. **Full System Testing** (Day 3)
   - Test MCP ↔ Agent integration
   - Verify A2A transaction flow
   - Monitor conversions and attribution

---

**Status**: Phase 4 🚀 Ready to Implement | UCP Readiness: 85% → 100%
