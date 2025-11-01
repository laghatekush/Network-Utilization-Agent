"""
Data processing module for warehouse utilization analysis
"""
import pandas as pd
from typing import Dict, List, Tuple

from config.settings import UTILIZATION_THRESHOLD


class WarehouseDataProcessor:
    """Processes warehouse data and calculates utilization metrics"""
    
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.df = None
        
    def load_data(self) -> pd.DataFrame:
        """Load warehouse data from Excel file"""
        try:
            self.df = pd.read_excel(self.excel_path)
            # Calculate utilization percentage if not present
            if 'Utilization_Percentage' not in self.df.columns:
                self.df['Utilization_Percentage'] = (
                    self.df['Current_Pallets'] / self.df['Total_Capacity_Pallets'] * 100
                ).round(2)
            return self.df
        except Exception as e:
            raise Exception(f"Error loading data: {str(e)}")
    
    def identify_utilization_issues(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Identify over-utilized and under-utilized warehouses
        Returns: (overutilized_df, underutilized_df)
        """
        if self.df is None:
            self.load_data()
            
        overutilized = self.df[
            self.df['Utilization_Percentage'] > UTILIZATION_THRESHOLD
        ].copy()
        
        underutilized = self.df[
            self.df['Utilization_Percentage'] < UTILIZATION_THRESHOLD
        ].copy()
        
        return overutilized, underutilized
    
    def group_by_region(self) -> Dict[str, pd.DataFrame]:
        """Group warehouses by region"""
        if self.df is None:
            self.load_data()
        
        regions = {}
        for region in self.df['Region'].unique():
            regions[region] = self.df[self.df['Region'] == region].copy()
        
        return regions
    
    def calculate_reallocation(self, overutilized: pd.DataFrame, 
                              underutilized: pd.DataFrame) -> List[Dict]:
        """
        Calculate pallet reallocation recommendations
        Returns list of recommendations with source, target, and pallet count
        """
        recommendations = []
        
        for region in overutilized['Region'].unique():
            # Get overutilized warehouses in this region
            over_in_region = overutilized[
                overutilized['Region'] == region
            ].copy()
            
            # Get underutilized warehouses in this region
            under_in_region = underutilized[
                underutilized['Region'] == region
            ].copy()
            
            if under_in_region.empty:
                continue
            
            for _, over_wh in over_in_region.iterrows():
                # Calculate excess pallets
                target_pallets = int(
                    over_wh['Total_Capacity_Pallets'] * (UTILIZATION_THRESHOLD / 100)
                )
                excess_pallets = over_wh['Current_Pallets'] - target_pallets
                
                if excess_pallets <= 0:
                    continue
                
                # Distribute excess to underutilized warehouses
                remaining_excess = excess_pallets
                
                for _, under_wh in under_in_region.iterrows():
                    if remaining_excess <= 0:
                        break
                    
                    # Calculate available capacity
                    target_capacity = int(
                        under_wh['Total_Capacity_Pallets'] * (UTILIZATION_THRESHOLD / 100)
                    )
                    available_space = target_capacity - under_wh['Current_Pallets']
                    
                    if available_space <= 0:
                        continue
                    
                    # Calculate pallets to move
                    pallets_to_move = min(remaining_excess, available_space)
                    
                    recommendations.append({
                        'region': region,
                        'from_warehouse': over_wh['Warehouse_ID'],
                        'from_name': over_wh['Warehouse_Name'],
                        'to_warehouse': under_wh['Warehouse_ID'],
                        'to_name': under_wh['Warehouse_Name'],
                        'pallets_to_move': int(pallets_to_move),
                        'from_current_util': over_wh['Utilization_Percentage'],
                        'to_current_util': under_wh['Utilization_Percentage'],
                        'branch_manager': over_wh['Branch_Manager_Name'],
                        'branch_email': over_wh['Branch_Manager_Email']
                    })
                    
                    remaining_excess -= pallets_to_move
        
        return recommendations
    
    def get_region_summary(self, region: str) -> pd.DataFrame:
        """Get summary of all warehouses in a region"""
        if self.df is None:
            self.load_data()
        
        return self.df[self.df['Region'] == region][[
            'Warehouse_ID', 'Warehouse_Name', 'Total_Capacity_Pallets',
            'Current_Pallets', 'Utilization_Percentage', 'Branch_Manager_Name'
        ]].copy()