"""
Native Checkout Service
File: src/checkout_service.py
Purpose: Native checkout orchestration for A2A transactions
Size: ~400 lines

Orchestrates complete checkout flow:
1. Initiate transaction
2. Validate inventory and pricing
3. Approve transaction (if needed)
4. Process payment
5. Create order
"""

from typing import Dict, Any, Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CheckoutService:
    """Orchestrate complete checkout flow for A2A transactions."""
    
    def __init__(self, a2a_router, merchant_client=None):
        self.a2a_router = a2a_router
        self.merchant_client = merchant_client
        self.logger = logging.getLogger(__name__)
    
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
            self.logger.info(f"[CHECKOUT] Initiating | Agent: {agent_id} | User: {user_id} | Items: {len(items)}")
            success, transaction = self.a2a_router.initiate_transaction(
                agent_id, user_id, items, metadata
            )
            if not success:
                return False, transaction
            
            transaction_id = transaction['transaction_id']
            
            # Step 2: Validate
            self.logger.info(f"[CHECKOUT] Validating | Transaction: {transaction_id}")
            is_valid, validation = self.a2a_router.validate_transaction(transaction_id)
            if not is_valid:
                return False, {"error": "Validation failed", "details": validation}
            
            # Step 3: Approve (optional, based on risk)
            self.logger.info(f"[CHECKOUT] Approving | Transaction: {transaction_id}")
            approved, approval = self.a2a_router.approve_transaction(transaction_id)
            if not approved:
                return False, {"error": "Transaction not approved"}
            
            # Step 4: Process Payment
            payment_details = metadata.get('payment_details', {}) if metadata else {}
            self.logger.info(f"[CHECKOUT] Processing payment | Transaction: {transaction_id}")
            pay_success, payment = self.a2a_router.process_payment(
                transaction_id, payment_method, payment_details
            )
            if not pay_success:
                return False, {"error": "Payment failed", "details": payment}
            
            # Step 5: Create Order
            self.logger.info(f"[CHECKOUT] Creating order | Transaction: {transaction_id}")
            order_success, order = self.a2a_router.create_order(transaction_id)
            if not order_success:
                return False, {"error": "Order creation failed"}
            
            self.logger.info(f"[CHECKOUT] SUCCESS | Order: {order['order_id']} | Transaction: {transaction_id}")
            
            return True, {
                "success": True,
                "order_id": order['order_id'],
                "transaction_id": transaction_id,
                "total": order['total'],
                "estimated_delivery": order['estimated_delivery']
            }
        
        except Exception as e:
            self.logger.error(f"[CHECKOUT] ERROR: {str(e)}")
            return False, {"error": str(e)}
    
    def get_checkout_session(self, transaction_id: str) -> Dict[str, Any]:
        """Get checkout session details."""
        transaction = self.a2a_router.get_transaction(transaction_id)
        
        if not transaction:
            return {"error": "Session not found"}
        
        return {
            "session_id": transaction_id,
            "status": transaction['status'],
            "items": transaction['items'],
            "total": sum(item['quantity'] * 29.99 for item in transaction['items']),
            "validation": transaction.get('validation'),
            "approval": transaction.get('approval'),
            "payment": transaction.get('payment'),
            "order": transaction.get('order')
        }
    
    def resume_checkout(self, transaction_id: str,
                       payment_method: str = "paystack") -> Tuple[bool, Dict[str, Any]]:
        """Resume a checkout that was interrupted."""
        transaction = self.a2a_router.get_transaction(transaction_id)
        
        if not transaction:
            return False, {"error": "Session not found"}
        
        # Continue from where we left off
        if transaction['status'] == 'initiated':
            return self.a2a_router.validate_transaction(transaction_id)
        
        elif transaction['status'] == 'validated':
            return self.a2a_router.approve_transaction(transaction_id)
        
        elif transaction['status'] == 'approved':
            return self.a2a_router.process_payment(transaction_id, payment_method)
        
        elif transaction['status'] == 'payment_processing':
            return self.a2a_router.create_order(transaction_id)
        
        else:
            return False, {"error": f"Cannot resume checkout in {transaction['status']} status"}
