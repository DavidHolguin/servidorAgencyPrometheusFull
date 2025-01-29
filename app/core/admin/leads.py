"""Lead management module."""
from typing import Dict, Any, Optional
from .base import BaseEntityManager

class LeadManager(BaseEntityManager):
    """Manager for lead operations."""
    
    def __init__(self, agency_id: str):
        super().__init__(agency_id, "leads")
        
    def get_lead_details(self, lead_id: str) -> Dict[str, Any]:
        """Get detailed information about a lead."""
        if not self.validate_ownership("leads", lead_id):
            return self.format_response(False, "Lead not found or access denied")
            
        # Get lead basic information
        lead = self.supabase.table("leads")\
            .select("*")\
            .eq("id", lead_id)\
            .execute()
            
        if not lead.data:
            return self.format_response(False, "Lead not found")
            
        # Get lead conversations
        conversations = self.supabase.table("chat_messages")\
            .select("*")\
            .eq("lead_id", lead_id)\
            .order("created_at", desc=True)\
            .execute()
            
        # Get lead bookings
        bookings = self.supabase.table("bookings")\
            .select("*")\
            .eq("lead_id", lead_id)\
            .order("created_at", desc=True)\
            .execute()
            
        # Get lead tracking data
        tracking = self.supabase.table("lead_tracking")\
            .select("*")\
            .eq("lead_id", lead_id)\
            .order("created_at", desc=True)\
            .execute()
            
        return self.format_response(True, "Lead details retrieved", {
            "lead": lead.data[0],
            "conversations": conversations.data,
            "bookings": bookings.data,
            "tracking": tracking.data
        })
    
    def update_lead_stage(self, lead_id: str, stage_id: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """Update the stage of a lead."""
        if not self.validate_ownership("leads", lead_id):
            return self.format_response(False, "Lead not found or access denied")
            
        # Validate stage belongs to agency
        stage = self.supabase.table("lead_stages")\
            .select("*")\
            .eq("id", stage_id)\
            .eq("agency_id", self.agency_id)\
            .execute()
            
        if not stage.data:
            return self.format_response(False, "Stage not found or access denied")
            
        # Create progress entry
        progress = self.supabase.table("lead_progress").insert({
            "lead_id": lead_id,
            "stage_id": stage_id,
            "notes": notes
        }).execute()
        
        return self.format_response(True, "Lead stage updated", {"progress": progress.data[0] if progress.data else None})
    
    def get_lead_stages(self) -> Dict[str, Any]:
        """Get all lead stages for the agency."""
        stages = self.supabase.table("lead_stages")\
            .select("*")\
            .eq("agency_id", self.agency_id)\
            .order("position")\
            .execute()
            
        return self.format_response(True, "Stages retrieved", {"stages": stages.data})
    
    def create_lead_stage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new lead stage."""
        required_fields = ["name", "color"]
        
        for field in required_fields:
            if field not in data:
                return self.format_response(False, f"Missing required field: {field}")
                
        # Get max position
        stages = self.supabase.table("lead_stages")\
            .select("position")\
            .eq("agency_id", self.agency_id)\
            .order("position", desc=True)\
            .limit(1)\
            .execute()
            
        data["position"] = (stages.data[0]["position"] + 1) if stages.data else 0
        data["agency_id"] = self.agency_id
        
        response = self.supabase.table("lead_stages").insert(data).execute()
        return self.format_response(True, "Stage created", {"stage": response.data[0] if response.data else None})
    
    def update_lead_stage_positions(self, stage_positions: Dict[str, int]) -> Dict[str, Any]:
        """Update positions of lead stages."""
        for stage_id, position in stage_positions.items():
            # Validate stage belongs to agency
            if not self.validate_ownership("lead_stages", stage_id):
                return self.format_response(False, f"Stage {stage_id} not found or access denied")
                
            self.supabase.table("lead_stages")\
                .update({"position": position})\
                .eq("id", stage_id)\
                .execute()
                
        return self.format_response(True, "Stage positions updated")
    
    def get_lead_stats(self) -> Dict[str, Any]:
        """Get lead statistics."""
        response = self.supabase.rpc(
            'get_lead_stats',
            {'p_agency_id': self.agency_id}
        ).execute()
        
        return self.format_response(True, "Statistics retrieved", response.data[0] if response.data else {})
    
    def get_leads_by_stage(self, stage_id: Optional[str] = None) -> Dict[str, Any]:
        """Get leads grouped by stage or for a specific stage."""
        query = self.supabase.table("leads")\
            .select("*, lead_progress(stage_id)")\
            .eq("agency_id", self.agency_id)
            
        if stage_id:
            query = query.eq("lead_progress.stage_id", stage_id)
            
        response = query.execute()
        
        return self.format_response(True, "Leads retrieved", {"leads": response.data})
