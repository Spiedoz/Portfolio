# Predicting Basket Player Career Longevity

## Overview
This project uses machine learning techniques to predict whether a basket player's career will last at least 5 years based on their performance statistics. We analyze various player metrics to identify key factors contributing to career longevity.

## Dataset
The dataset contains 1340 observations and 21 variables, including:
- Games played
- Points scored
- Rebounds
- Assists
- Steals
- Blocks
and more.

The target variable is binary: 0 for careers less than 5 years, 1 for careers of 5 years or more.
For more information about the dataset, check the link: https://www.kaggle.com/datasets/sachinsharma1123/performance-prediction/data.

## Methodology
1. Exploratory Data Analysis (EDA)
2. Data preprocessing and feature selection
3. Model development:
   - Decision Tree
   - Random Forest
   - Logistic Regression (with Lasso and Ridge regularization)
4. Model evaluation using ROC curves and confusion matrices
5. Model improvement through oversampling techniques

## Key Findings
- The Random Forest model, after improvement with oversampling, performed best in predicting player career longevity.
- Key predictors of career longevity include GamesPlayed, FieldGoalPercent, FreeThrowPercent.
- The other models differ little from each other.

## File Structure
- `BasketPlayerCareer.qmd`: Quarto document containing the full analysis, including R code and visualizations.
- `player_performance.csv`: CSV file containing records about the players.
- `player_performance.html`: HTML file to show the graphs of the report 

## Requirements
- R (version 4.3.2. or higher)
- R packages: [dplyr, tidyr, caret, glmnet, randomForest, rpart, ggplot2, rpart.plot, pROC, e1071]
- Quarto

## How to Run
1. Clone this repository
2. Install required R packages: `install.packages(c("package1", "package2", ...))`
3. Open the `BasketPlayerCareer.qmd` file in RStudio or your preferred Quarto-compatible IDE
4. Render the Quarto document to view the full report with code, analysis, and visualizations

## Future Work
- Incorporate more recent player data
- Explore additional machine learning algorithms
- Include more variables to uncover potential factors influencing longevity of players' careers

## Author
Giorgio Boi
