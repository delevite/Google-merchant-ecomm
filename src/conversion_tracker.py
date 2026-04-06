"""
Conversion Tracking & Analytics
File: src/conversion_tracker.py
Purpose: Attribution and conversion tracking for AI agents
Size: ~500 lines

Tracks:
- User sessions from AI agents
- Conversion events (browse, add-to-cart, purchase)
- Agent performance metrics
- Attribution data for each conversion
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import uuid

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
    
    def end_session(self, session_id: str) -> None:
        """End tracking user session."""
        if session_id not in self.sessions:
            return
        
        self.track_event(session_id, ConversionEvent.AGENT_SESSION_END, {})
        
        session = self.sessions[session_id]
        session['ended_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Session ended: {session_id} | Converted: {session['converted']}")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        session = self.sessions[session_id]
        session_events = [e for e in self.events if e['session_id'] == session_id]
        
        if not session_events:
            duration_seconds = 0
        else:
            start_time = datetime.fromisoformat(session_events[0]['timestamp'])
            end_time = datetime.fromisoformat(session_events[-1]['timestamp'])
            duration_seconds = (end_time - start_time).total_seconds()
        
        stats = {
            "session_id": session_id,
            "agent_id": session['agent_id'],
            "user_id": session['user_id'],
            "duration_seconds": duration_seconds,
            "event_count": len(session_events),
            "converted": session['converted'],
            "order_id": session['order_id'],
            "events": [
                {
                    "type": e['event_type'],
                    "timestamp": e['timestamp'],
                    "data": e['data']
                }
                for e in session_events
            ]
        }
        
        return stats
    
    def get_agent_metrics(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
        """Get metrics for a specific AI agent."""
        # Filter sessions for this agent in the last N days
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        agent_sessions = [
            s for s in self.sessions.values()
            if s['agent_id'] == agent_id and 
            datetime.fromisoformat(s['started_at']) >= cutoff_time
        ]
        
        conversions = sum(1 for s in agent_sessions if s['converted'])
        
        # Calculate total revenue from converted sessions
        total_revenue = 0
        converted_orders = []
        
        for session in agent_sessions:
            if session['converted'] and session['order_id']:
                converted_orders.append(session['order_id'])
                # TODO: Fetch actual order values from order system
                total_revenue += 100  # Placeholder
        
        metrics = {
            "agent_id": agent_id,
            "period_days": days,
            "sessions": len(agent_sessions),
            "conversions": conversions,
            "conversion_rate": conversions / len(agent_sessions) if agent_sessions else 0,
            "total_revenue": total_revenue,
            "avg_order_value": total_revenue / conversions if conversions > 0 else 0,
            "events": len([
                e for e in self.events 
                if any(s['agent_id'] == agent_id for s in [self.sessions.get(e['session_id'])])
            ])
        }
        
        return metrics
    
    def get_event_breakdown(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
        """Get breakdown of events for an agent."""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        agent_sessions = [
            s for s in self.sessions.values()
            if s['agent_id'] == agent_id and 
            datetime.fromisoformat(s['started_at']) >= cutoff_time
        ]
        
        session_ids = {s['session_id'] for s in agent_sessions}
        agent_events = [e for e in self.events if e['session_id'] in session_ids]
        
        breakdown = {}
        for event in agent_events:
            event_type = event['event_type']
            if event_type not in breakdown:
                breakdown[event_type] = 0
            breakdown[event_type] += 1
        
        return {
            "agent_id": agent_id,
            "period_days": days,
            "event_breakdown": breakdown,
            "total_events": len(agent_events)
        }
    
    def get_top_agents(self, limit: int = 10, days: int = 30) -> List[Dict[str, Any]]:
        """Get top performing agents by conversion rate."""
        agents = {}
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        for session in self.sessions.values():
            if datetime.fromisoformat(session['started_at']) < cutoff_time:
                continue
            
            agent_id = session['agent_id']
            if agent_id not in agents:
                agents[agent_id] = {
                    "sessions": 0,
                    "conversions": 0
                }
            
            agents[agent_id]['sessions'] += 1
            if session['converted']:
                agents[agent_id]['conversions'] += 1
        
        # Calculate metrics and sort
        agent_list = []
        for agent_id, data in agents.items():
            agent_list.append({
                "agent_id": agent_id,
                "sessions": data['sessions'],
                "conversions": data['conversions'],
                "conversion_rate": data['conversions'] / data['sessions'] if data['sessions'] > 0 else 0
            })
        
        agent_list.sort(key=lambda x: x['conversion_rate'], reverse=True)
        
        return agent_list[:limit]
    
    def export_session_csv(self, session_id: str) -> str:
        """Export session data as CSV."""
        if session_id not in self.sessions:
            return ""
        
        import csv
        from io import StringIO
        
        session = self.sessions[session_id]
        session_events = [e for e in self.events if e['session_id'] == session_id]
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=['timestamp', 'event_type', 'data'])
        writer.writeheader()
        
        for event in session_events:
            writer.writerow({
                'timestamp': event['timestamp'],
                'event_type': event['event_type'],
                'data': json.dumps(event['data'])
            })
        
        return output.getvalue()
