/**
 * Test file for planning state handler
 * This file can be used to verify the handler works correctly with sample data
 */

import { convertPlanningStateToText } from './planning-state-handler'

// Sample planning state for testing
const samplePlanningState = {
  experiment_id: "exp_123",
  research_query: "What is the effect of caffeine on cognitive performance in university students?",
  experiment_objective: "To determine whether caffeine consumption improves cognitive performance measured by reaction time and working memory tasks in university students aged 18-25.",
  hypothesis: "Caffeine consumption will significantly improve reaction time and working memory performance compared to placebo.",
  
  independent_variables: [
    {
      name: "Caffeine dose",
      type: "categorical",
      units: "mg",
      levels: ["0", "100", "200"]
    }
  ],
  
  dependent_variables: [
    {
      name: "Reaction time",
      type: "continuous",
      units: "milliseconds",
      measurement_method: "Computer-based reaction time task"
    },
    {
      name: "Working memory score",
      type: "continuous",
      units: "points",
      measurement_method: "N-back task accuracy percentage"
    }
  ],
  
  control_variables: [
    {
      name: "Time of day",
      reason: "Circadian rhythms affect cognitive performance",
      control_method: "All testing conducted between 9-11 AM"
    },
    {
      name: "Sleep quality",
      reason: "Sleep affects cognitive performance",
      control_method: "Participants must have 7+ hours sleep night before"
    }
  ],
  
  experimental_groups: [
    {
      name: "Control Group",
      description: "Participants receive placebo (0mg caffeine)",
      conditions: {
        caffeine_dose: "0mg",
        beverage: "Decaffeinated coffee"
      }
    },
    {
      name: "Low Dose Group",
      description: "Participants receive 100mg caffeine",
      conditions: {
        caffeine_dose: "100mg",
        beverage: "Coffee with 100mg caffeine"
      }
    },
    {
      name: "High Dose Group", 
      description: "Participants receive 200mg caffeine",
      conditions: {
        caffeine_dose: "200mg",
        beverage: "Coffee with 200mg caffeine"
      }
    }
  ],
  
  sample_size: {
    biological_replicates: 30,
    power_analysis: "Power analysis indicates n=30 per group provides 80% power to detect medium effect size"
  },
  
  methodology_steps: [
    {
      step_number: 1,
      description: "Participant screening and consent",
      parameters: {
        inclusion_criteria: "Age 18-25, university student, regular coffee drinker",
        exclusion_criteria: "Pregnancy, heart conditions, caffeine sensitivity"
      },
      duration: "30 minutes"
    },
    {
      step_number: 2,
      description: "Baseline cognitive testing",
      parameters: {
        tests: "Reaction time task, N-back task",
        duration_per_task: "10 minutes"
      },
      duration: "30 minutes"
    },
    {
      step_number: 3,
      description: "Caffeine/placebo administration",
      parameters: {
        administration_method: "Oral consumption",
        blinding: "Double-blind"
      },
      duration: "5 minutes"
    },
    {
      step_number: 4,
      description: "Wait period for caffeine absorption",
      parameters: {
        activity: "Quiet reading or relaxation"
      },
      duration: "45 minutes"
    },
    {
      step_number: 5,
      description: "Post-treatment cognitive testing",
      parameters: {
        tests: "Same as baseline",
        test_order: "Counterbalanced"
      },
      duration: "30 minutes"
    }
  ],
  
  materials_equipment: [
    {
      name: "Computer workstation",
      type: "Hardware",
      quantity: "3 units",
      specifications: "Windows 10, 24-inch monitor, standard keyboard/mouse"
    },
    {
      name: "Caffeine capsules",
      type: "Consumable",
      quantity: "180 capsules",
      specifications: "100mg and 200mg pharmaceutical grade caffeine"
    },
    {
      name: "Placebo capsules",
      type: "Consumable", 
      quantity: "90 capsules",
      specifications: "Identical appearance to caffeine capsules, containing inert filler"
    }
  ],
  
  data_collection_plan: {
    methods: ["Computer-based task recording", "Manual data entry"],
    timing: "Single session per participant, 3 weeks total data collection",
    formats: ["CSV files", "SPSS format"]
  },
  
  data_analysis_plan: {
    statistical_tests: ["Repeated measures ANOVA", "Post-hoc t-tests", "Effect size calculations"],
    visualizations: ["Bar charts with error bars", "Scatter plots", "Box plots"],
    software: ["R", "SPSS", "ggplot2"]
  },
  
  expected_outcomes: "We expect to see improved reaction times and working memory scores in the caffeine groups compared to placebo, with the high dose group showing the greatest improvement.",
  
  potential_pitfalls: [
    {
      issue: "Participant caffeine tolerance",
      likelihood: "Medium",
      mitigation: "Screen for regular caffeine consumption patterns and exclude heavy users"
    },
    {
      issue: "Practice effects on cognitive tasks",
      likelihood: "High", 
      mitigation: "Include practice sessions and counterbalance test order"
    }
  ],
  
  ethical_considerations: "IRB approval required. Participants will be informed of caffeine content and potential side effects. Medical screening for contraindications to caffeine.",
  
  timeline: {
    "Recruitment": "2 weeks",
    "Data collection": "3 weeks", 
    "Data analysis": "2 weeks",
    "Report writing": "2 weeks"
  },
  
  budget_estimate: {
    "Participant compensation": "$1800",
    "Materials and supplies": "$500",
    "Equipment rental": "$300",
    "Total": "$2600"
  },
  
  // System fields that should be filtered out
  current_stage: "final_review",
  errors: [],
  chat_history: [
    {
      timestamp: "2024-01-15T10:30:00Z",
      role: "user", 
      content: "I want to study caffeine effects on cognition"
    },
    {
      timestamp: "2024-01-15T10:35:00Z",
      role: "assistant",
      content: "Great! Let's design a controlled experiment..."
    }
  ]
}

// Test the conversion
export function testPlanningStateHandler(): string {
  console.log("Testing planning state handler...")
  
  try {
    const result = convertPlanningStateToText(samplePlanningState)
    console.log("✅ Planning state converted successfully")
    console.log("📄 Generated text length:", result.length, "characters")
    
    // Check if key sections are present
    const expectedSections = [
      "# Experiment Plan",
      "## Research Query", 
      "## Objective",
      "## Hypothesis",
      "## Variables",
      "## Experimental Design", 
      "## Methodology",
      "## Data Collection & Analysis",
      "## Risk Assessment",
      "## Administrative Details",
      "## Planning Status"
    ]
    
    const missingSections = expectedSections.filter(section => !result.includes(section))
    
    if (missingSections.length === 0) {
      console.log("✅ All expected sections present")
    } else {
      console.log("⚠️ Missing sections:", missingSections)
    }
    
    // Check that system fields are not in the output
    const systemFields = ["chat_history", "current_stage", "errors", "experiment_id"]
    const foundSystemFields = systemFields.filter(field => result.includes(field))
    
    if (foundSystemFields.length === 0) {
      console.log("✅ System fields properly filtered out")
    } else {
      console.log("⚠️ System fields found in output:", foundSystemFields)
    }
    
    return result
    
  } catch (error) {
    console.error("❌ Error testing planning state handler:", error)
    return `Error: ${error}`
  }
}

// Uncomment to run test
// console.log(testPlanningStateHandler())