#!/usr/bin/env python3
"""
Test script to demonstrate semantic understanding functionality 
for biomedical data analysis.
"""

import os
import sys
import pandas as pd
import asyncio
from io import StringIO

# Add the server directory to sys.path so we can import our modules
server_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, server_path)

from agents.dataclean.quality_agent import DataQualityAgent
from config import get_openai_client


def create_sample_biomedical_data():
    """Create sample biomedical datasets for testing."""
    
    # Sample 1: C. elegans behavioral study
    celegans_data = """
Subject_ID,Treatment_Group,CO2_Concentration_ppm,Behavioral_Score,Response_Time_sec,Temperature_C,Worm_Strain
W001,Control,350,7.2,12.5,20,N2
W002,Control,350,8.1,11.8,20,N2
W003,High_CO2,1000,4.3,18.2,20,N2
W004,High_CO2,1000,3.8,19.5,20,N2
W005,Control,350,7.8,12.1,20,daf-2
W006,Control,350,8.3,11.2,20,daf-2
W007,High_CO2,1000,5.1,17.8,20,daf-2
W008,High_CO2,1000,4.9,18.9,20,daf-2
"""
    
    # Sample 2: Gene expression study
    gene_expression_data = """
Sample_ID,Treatment,Gene_BRCA1_Expression,Gene_TP53_Expression,Gene_MYC_Expression,Patient_Age,Cancer_Stage,Tumor_Size_mm
S001,Chemotherapy,2.4,1.8,3.2,45,II,15
S002,Chemotherapy,2.1,1.6,3.8,52,III,22
S003,Control,4.2,3.1,1.9,38,I,8
S004,Control,4.5,2.8,2.1,41,I,9
S005,Radiation,1.8,1.2,4.1,58,III,28
S006,Radiation,1.9,1.4,3.9,62,IV,35
"""
    
    # Sample 3: Drug screening study
    drug_screening_data = """
Compound_ID,Drug_Name,Concentration_uM,Cell_Viability_Percent,IC50_uM,Cell_Line,Assay_Type,Incubation_Hours
C001,Doxorubicin,0.1,95.2,0.85,HeLa,MTT,24
C002,Doxorubicin,1.0,78.4,0.85,HeLa,MTT,24
C003,Doxorubicin,10.0,42.1,0.85,HeLa,MTT,24
C004,Cisplatin,0.5,88.7,2.1,HeLa,MTT,24
C005,Cisplatin,5.0,65.2,2.1,HeLa,MTT,24
C006,Cisplatin,50.0,31.8,2.1,HeLa,MTT,24
"""
    
    return {
        "celegans_co2_study": celegans_data,
        "gene_expression_study": gene_expression_data,
        "drug_screening_study": drug_screening_data
    }


async def test_semantic_understanding():
    """Test the semantic understanding functionality."""
    
    print("🧬 Testing Semantic Understanding for Biomedical Data")
    print("=" * 60)
    
    # Initialize the quality agent
    openai_client = get_openai_client()
    if not openai_client:
        print("❌ OpenAI client not available. Please check your configuration.")
        return
    
    quality_agent = DataQualityAgent(openai_client)
    
    # Get sample datasets
    sample_datasets = create_sample_biomedical_data()
    
    for dataset_name, csv_data in sample_datasets.items():
        print(f"\n📊 Analyzing: {dataset_name}")
        print("-" * 40)
        
        # Parse CSV data
        df = pd.read_csv(StringIO(csv_data))
        print(f"Dataset shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        
        # Perform semantic analysis
        try:
            semantic_analysis = await quality_agent.understand_data_semantics(df)
            
            if semantic_analysis.get("success"):
                print("\n🔬 Data Understanding:")
                print(f"   {semantic_analysis.get('data_understanding', 'N/A')}")
                
                print(f"\n📊 Research Domain: {semantic_analysis.get('research_domain', 'N/A')}")
                
                experimental_design = semantic_analysis.get('experimental_design', 'N/A')
                if experimental_design != "Could not determine":
                    print(f"\n🧪 Experimental Design:")
                    print(f"   {experimental_design}")
                
                key_variables = semantic_analysis.get('key_variables', [])
                if key_variables:
                    print(f"\n🔑 Key Variables ({len(key_variables)} identified):")
                    for var in key_variables:
                        role = var.get('role', 'unknown')
                        name = var.get('name', 'Unknown')
                        description = var.get('description', 'No description')
                        print(f"   • {name} ({role}): {description}")
                
                confidence = semantic_analysis.get('analysis_confidence', 0.0)
                print(f"\n📈 Analysis Confidence: {confidence:.2f}")
                
            else:
                print(f"❌ Analysis failed: {semantic_analysis.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Error during semantic analysis: {str(e)}")
        
        print()


def test_traditional_vs_semantic():
    """Compare traditional describe vs semantic understanding."""
    
    print("\n🔄 Traditional vs Semantic Analysis Comparison")
    print("=" * 60)
    
    # Create a sample dataset
    sample_data = create_sample_biomedical_data()["celegans_co2_study"]
    df = pd.read_csv(StringIO(sample_data))
    
    print("📈 Traditional Description (Basic Info):")
    print(f"   Shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Data types: {df.dtypes.to_dict()}")
    print(f"   Missing values: {df.isnull().sum().sum()}")
    
    print("\n🔬 Enhanced Semantic Understanding:")
    print("   (This would provide context like 'C. elegans behavioral study')")
    print("   (Identifies experimental design, key variables, research domain)")
    print("   (Understands what the data represents, not just its structure)")


if __name__ == "__main__":
    print("🚀 Starting Semantic Understanding Tests")
    
    # Test with sample data
    test_traditional_vs_semantic()
    
    # Test with real AI analysis (requires OpenAI API key)
    try:
        asyncio.run(test_semantic_understanding())
    except Exception as e:
        print(f"\n❌ Could not run AI-powered semantic analysis: {str(e)}")
        print("   This likely means OpenAI API key is not configured.")
        print("   The functionality will still work when properly configured.")
    
    print("\n✅ Test completed!")
    print("\nTo use this feature:")
    print("1. Upload your biomedical data")
    print("2. Ask to 'describe' your data")
    print("3. The system will now provide intelligent insights about your research!") 