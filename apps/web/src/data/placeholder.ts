/**
 * Placeholder data for the ScioScribe application
 * 
 * This module contains sample datasets that can be used for testing
 * and demonstration purposes.
 */

// Comprehensive Iris Dataset - Classic machine learning dataset
export const IRIS_CSV_DATA = `sepal_length,sepal_width,petal_length,petal_width,species
5.1,3.5,1.4,0.2,setosa
4.9,3.0,1.4,0.2,setosa
4.7,3.2,1.3,0.2,setosa
4.6,3.1,1.5,0.2,setosa
5.0,3.6,1.4,0.2,setosa
5.4,3.9,1.7,0.4,setosa
4.6,3.4,1.4,0.3,setosa
5.0,3.4,1.5,0.2,setosa
4.4,2.9,1.4,0.2,setosa
4.9,3.1,1.5,0.1,setosa
5.4,3.7,1.5,0.2,setosa
4.8,3.4,1.6,0.2,setosa
4.8,3.0,1.4,0.1,setosa
4.3,3.0,1.1,0.1,setosa
5.8,4.0,1.2,0.2,setosa
5.7,4.4,1.5,0.4,setosa
5.4,3.9,1.3,0.4,setosa
5.1,3.5,1.4,0.3,setosa
5.7,3.8,1.7,0.3,setosa
5.1,3.8,1.5,0.3,setosa
5.4,3.4,1.7,0.2,setosa
5.1,3.7,1.5,0.4,setosa
4.6,3.6,1.0,0.2,setosa
5.1,3.3,1.7,0.5,setosa
4.8,3.4,1.9,0.2,setosa
7.0,3.2,4.7,1.4,versicolor
6.4,3.2,4.5,1.5,versicolor
6.9,3.1,4.9,1.5,versicolor
5.5,2.3,4.0,1.3,versicolor
6.5,2.8,4.6,1.5,versicolor
5.7,2.8,4.5,1.3,versicolor
6.3,3.3,4.7,1.6,versicolor
4.9,2.4,3.3,1.0,versicolor
6.6,2.9,4.6,1.3,versicolor
5.2,2.7,3.9,1.4,versicolor
5.0,2.0,3.5,1.0,versicolor
5.9,3.0,4.2,1.5,versicolor
6.0,2.2,4.0,1.0,versicolor
6.1,2.9,4.7,1.4,versicolor
5.6,2.9,3.6,1.3,versicolor
6.7,3.1,4.4,1.4,versicolor
5.6,3.0,4.5,1.5,versicolor
5.8,2.7,4.1,1.0,versicolor
6.2,2.2,4.5,1.5,versicolor
5.6,2.5,3.9,1.1,versicolor
5.9,3.2,4.8,1.8,versicolor
6.1,2.8,4.0,1.3,versicolor
6.3,2.5,4.9,1.5,versicolor
6.1,2.8,4.7,1.2,versicolor
6.4,2.9,4.3,1.3,versicolor
6.3,3.3,6.0,2.5,virginica
5.8,2.7,5.1,1.9,virginica
7.1,3.0,5.9,2.1,virginica
6.3,2.9,5.6,1.8,virginica
6.5,3.0,5.8,2.2,virginica
7.6,3.0,6.6,2.1,virginica
4.9,2.5,4.5,1.7,virginica
7.3,2.9,6.3,1.8,virginica
6.7,2.5,5.8,1.8,virginica
7.2,3.6,6.1,2.5,virginica
6.5,3.2,5.1,2.0,virginica
6.4,2.7,5.3,1.9,virginica
6.8,3.0,5.5,2.1,virginica
5.7,2.5,5.0,2.0,virginica
5.8,2.8,5.1,2.4,virginica
6.4,3.2,5.3,2.3,virginica
6.5,3.0,5.5,1.8,virginica
7.7,3.8,6.7,2.2,virginica
7.7,2.6,6.9,2.3,virginica
6.0,2.2,5.0,1.5,virginica
6.9,3.2,5.7,2.3,virginica
5.6,2.8,4.9,2.0,virginica
7.7,2.8,6.7,2.0,virginica
6.3,2.7,4.9,1.8,virginica
6.7,3.3,5.7,2.1,virginica`

// Sample experiment plan for iris analysis
export const IRIS_EXPERIMENT_PLAN = `# Iris Species Classification Analysis

## Objective
Analyze the morphological characteristics of iris flowers to understand the relationship between sepal and petal measurements across different species (setosa, versicolor, and virginica).

## Data Description
- **Dataset**: Iris flower measurements
- **Features**: Sepal length, sepal width, petal length, petal width (in cm)
- **Target**: Species classification (3 classes)
- **Sample Size**: 75 observations across 3 species

## Research Questions
1. How do sepal measurements correlate with petal measurements?
2. Which features best distinguish between iris species?
3. What are the characteristic ranges for each species?
4. Can we identify clustering patterns in the morphological data?

## Analysis Steps
1. **Exploratory Data Analysis**
   - Summary statistics for each species
   - Distribution analysis of measurements
   - Correlation analysis between features

2. **Visualization**
   - Scatter plots of feature relationships
   - Box plots for species comparison
   - Correlation heatmaps
   - Pair plots for multivariate analysis

3. **Statistical Analysis**
   - ANOVA tests for species differences
   - Principal component analysis
   - Cluster analysis validation

## Expected Outcomes
- Clear species differentiation patterns
- Feature importance rankings
- Visual insights into morphological relationships
- Statistical validation of species clusters

## Quality Checks
- Data completeness verification
- Outlier detection and analysis
- Statistical significance testing
- Cross-validation of findings`

// Parse CSV data into structured format for table display
export function parseCSVData(csvString: string): Array<Record<string, string>> {
  const lines = csvString.trim().split('\n')
  const headers = lines[0].split(',')
  
  return lines.slice(1).map((line, index) => {
    const values = line.split(',')
    const row: Record<string, string> = { id: (index + 1).toString() }
    
    headers.forEach((header, i) => {
      row[header] = values[i] || ''
    })
    
    return row
  })
}

// Get CSV headers
export function getCSVHeaders(csvString: string): string[] {
  return csvString.trim().split('\n')[0].split(',')
}

// Sample prompts for different analysis types
export const SAMPLE_PROMPTS = {
  visualization: [
    "Create a scatter plot showing the relationship between sepal length and sepal width, colored by species",
    "Generate a box plot comparing petal lengths across different iris species",
    "Show a correlation heatmap of all numeric features in the iris dataset",
    "Create a pair plot to visualize relationships between all measurements by species"
  ],
  analysis: [
    "Analyze the statistical differences between iris species",
    "Identify which features best distinguish between species",
    "Examine the correlation patterns in the iris measurements",
    "Investigate clustering patterns in the morphological data"
  ],
  insights: [
    "What are the key characteristics that distinguish setosa from other species?",
    "Which measurements show the highest variability within species?",
    "Are there any unusual patterns or outliers in the data?",
    "How do petal and sepal measurements relate to each other?"
  ]
}

// Export individual species data for specific analysis
export const SPECIES_DATA = {
  setosa: IRIS_CSV_DATA.split('\n').slice(0, 26).join('\n'),
  versicolor: [IRIS_CSV_DATA.split('\n')[0], ...IRIS_CSV_DATA.split('\n').slice(26, 51)].join('\n'),
  virginica: [IRIS_CSV_DATA.split('\n')[0], ...IRIS_CSV_DATA.split('\n').slice(51)].join('\n')
} 