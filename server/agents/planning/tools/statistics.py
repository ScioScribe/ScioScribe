"""
Statistical calculation tools for experiment planning agents.

This module provides comprehensive statistical analysis tools including power calculations,
effect size estimates, sample size determination, and statistical test recommendations
for robust experimental design.
"""

import math
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

try:
    import numpy as np
    from scipy import stats
    from scipy.stats import t, norm, chi2, f
    import statsmodels.stats.power as smp
    from statsmodels.stats.proportion import proportions_ztest
    from statsmodels.stats.contingency_tables import mcnemar
except ImportError:
    # Fallback for basic calculations without scipy/statsmodels
    np = None
    stats = None
    smp = None


logger = logging.getLogger(__name__)


class StatisticalTestType(str, Enum):
    """Types of statistical tests for experimental design."""
    TWO_SAMPLE_TTEST = "two_sample_ttest"
    ONE_WAY_ANOVA = "one_way_anova"
    TWO_WAY_ANOVA = "two_way_anova"
    PAIRED_TTEST = "paired_ttest"
    MANN_WHITNEY = "mann_whitney"
    KRUSKAL_WALLIS = "kruskal_wallis"
    WILCOXON = "wilcoxon"
    CHI_SQUARE = "chi_square"
    FISHERS_EXACT = "fishers_exact"
    PEARSON_CORRELATION = "pearson_correlation"
    SPEARMAN_CORRELATION = "spearman_correlation"
    LINEAR_REGRESSION = "linear_regression"
    LOGISTIC_REGRESSION = "logistic_regression"


class EffectSize(str, Enum):
    """Standard effect size categories."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    VERY_LARGE = "very_large"


@dataclass
class PowerAnalysisResult:
    """Result of statistical power analysis."""
    test_type: StatisticalTestType
    effect_size: float
    sample_size: int
    power: float
    alpha: float
    groups: int
    effect_size_category: str
    recommendations: List[str]
    assumptions: List[str]
    alternative_tests: List[str]
    confidence_interval: Optional[Tuple[float, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "test_type": self.test_type.value,
            "effect_size": self.effect_size,
            "sample_size": self.sample_size,
            "power": self.power,
            "alpha": self.alpha,
            "groups": self.groups,
            "effect_size_category": self.effect_size_category,
            "recommendations": self.recommendations,
            "assumptions": self.assumptions,
            "alternative_tests": self.alternative_tests,
            "confidence_interval": self.confidence_interval
        }


@dataclass
class SampleSizeResult:
    """Result of sample size calculation."""
    required_sample_size: int
    total_sample_size: int
    power_achieved: float
    effect_size: float
    alpha: float
    test_type: StatisticalTestType
    practical_considerations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "required_sample_size": self.required_sample_size,
            "total_sample_size": self.total_sample_size,
            "power_achieved": self.power_achieved,
            "effect_size": self.effect_size,
            "alpha": self.alpha,
            "test_type": self.test_type.value,
            "practical_considerations": self.practical_considerations
        }


class StatisticalCalculator:
    """
    Comprehensive statistical calculator for experiment planning.
    
    Provides power analysis, sample size calculations, effect size estimates,
    and statistical test recommendations for experimental design.
    """
    
    def __init__(self, log_level: str = "INFO"):
        """
        Initialize the statistical calculator.
        
        Args:
            log_level: Logging level for the calculator
        """
        self.logger = logging.getLogger(f"planning.tools.statistics")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Check if statistical libraries are available
        self.has_scipy = np is not None and stats is not None
        self.has_statsmodels = smp is not None
        
        if not self.has_scipy:
            self.logger.warning("SciPy not available. Statistical calculations will be limited.")
        if not self.has_statsmodels:
            self.logger.warning("StatsModels not available. Advanced power analysis will be limited.")
    
    def calculate_power_analysis(
        self,
        test_type: StatisticalTestType,
        effect_size: float,
        sample_size: Optional[int] = None,
        power: Optional[float] = None,
        alpha: float = 0.05,
        groups: int = 2,
        **kwargs
    ) -> PowerAnalysisResult:
        """
        Calculate statistical power analysis for experimental design.
        
        Args:
            test_type: Type of statistical test
            effect_size: Expected effect size (Cohen's d, eta-squared, etc.)
            sample_size: Sample size per group (if known)
            power: Desired power (if calculating sample size)
            alpha: Significance level
            groups: Number of groups
            **kwargs: Additional test-specific parameters
            
        Returns:
            PowerAnalysisResult with analysis details
        """
        try:
            # Validate inputs
            if not (0 < alpha < 1):
                raise ValueError("Alpha must be between 0 and 1")
            if power is not None and not (0 < power < 1):
                raise ValueError("Power must be between 0 and 1")
            if sample_size is not None and sample_size <= 0:
                raise ValueError("Sample size must be positive")
            
            # Perform power analysis based on test type
            if test_type == StatisticalTestType.TWO_SAMPLE_TTEST:
                result = self._power_ttest_two_sample(effect_size, sample_size, power, alpha)
            elif test_type == StatisticalTestType.ONE_WAY_ANOVA:
                result = self._power_anova_one_way(effect_size, sample_size, power, alpha, groups)
            elif test_type == StatisticalTestType.PAIRED_TTEST:
                result = self._power_ttest_paired(effect_size, sample_size, power, alpha)
            elif test_type == StatisticalTestType.CHI_SQUARE:
                result = self._power_chi_square(effect_size, sample_size, power, alpha, **kwargs)
            elif test_type == StatisticalTestType.PEARSON_CORRELATION:
                result = self._power_correlation(effect_size, sample_size, power, alpha)
            else:
                # Fallback to basic t-test calculation
                result = self._power_ttest_two_sample(effect_size, sample_size, power, alpha)
            
            # Add metadata
            result.test_type = test_type
            result.effect_size_category = self._categorize_effect_size(effect_size, test_type)
            result.recommendations = self._generate_recommendations(result)
            result.assumptions = self._get_test_assumptions(test_type)
            result.alternative_tests = self._suggest_alternative_tests(test_type)
            
            self.logger.info(f"Power analysis completed for {test_type.value}")
            return result
            
        except Exception as e:
            self.logger.error(f"Power analysis failed: {str(e)}")
            # Return fallback result
            return self._create_fallback_power_result(test_type, effect_size, alpha)
    
    def calculate_sample_size(
        self,
        test_type: StatisticalTestType,
        effect_size: float,
        power: float = 0.8,
        alpha: float = 0.05,
        groups: int = 2,
        **kwargs
    ) -> SampleSizeResult:
        """
        Calculate required sample size for desired power.
        
        Args:
            test_type: Type of statistical test
            effect_size: Expected effect size
            power: Desired statistical power
            alpha: Significance level
            groups: Number of groups
            **kwargs: Additional test-specific parameters
            
        Returns:
            SampleSizeResult with sample size recommendations
        """
        try:
            # Calculate power analysis to get sample size
            power_result = self.calculate_power_analysis(
                test_type=test_type,
                effect_size=effect_size,
                power=power,
                alpha=alpha,
                groups=groups,
                **kwargs
            )
            
            # Calculate total sample size
            total_sample = power_result.sample_size * groups
            
            # Generate practical considerations
            practical_considerations = self._generate_practical_considerations(
                power_result.sample_size, groups, test_type
            )
            
            return SampleSizeResult(
                required_sample_size=power_result.sample_size,
                total_sample_size=total_sample,
                power_achieved=power_result.power,
                effect_size=effect_size,
                alpha=alpha,
                test_type=test_type,
                practical_considerations=practical_considerations
            )
            
        except Exception as e:
            self.logger.error(f"Sample size calculation failed: {str(e)}")
            # Return fallback result
            return self._create_fallback_sample_size_result(test_type, effect_size, power, alpha)
    
    def recommend_statistical_test(
        self,
        independent_variables: List[Dict[str, Any]],
        dependent_variables: List[Dict[str, Any]],
        experimental_groups: List[Dict[str, Any]],
        study_design: str = "between_subjects"
    ) -> List[Dict[str, Any]]:
        """
        Recommend appropriate statistical tests based on experimental design.
        
        Args:
            independent_variables: List of independent variables
            dependent_variables: List of dependent variables
            experimental_groups: List of experimental groups
            study_design: Study design type (between_subjects, within_subjects, mixed)
            
        Returns:
            List of recommended statistical tests with details
        """
        recommendations = []
        
        try:
            # Analyze experimental design
            num_groups = len(experimental_groups)
            iv_count = len(independent_variables)
            dv_count = len(dependent_variables)
            
            # Primary analysis recommendations
            if num_groups == 2 and dv_count == 1:
                if study_design == "between_subjects":
                    recommendations.append({
                        "test": StatisticalTestType.TWO_SAMPLE_TTEST.value,
                        "description": "Independent samples t-test",
                        "assumptions": ["Normal distribution", "Equal variances", "Independent observations"],
                        "alternative": StatisticalTestType.MANN_WHITNEY.value,
                        "priority": "primary"
                    })
                else:
                    recommendations.append({
                        "test": StatisticalTestType.PAIRED_TTEST.value,
                        "description": "Paired samples t-test",
                        "assumptions": ["Normal distribution of differences", "Independent pairs"],
                        "alternative": StatisticalTestType.WILCOXON.value,
                        "priority": "primary"
                    })
            
            elif num_groups > 2 and dv_count == 1:
                if iv_count == 1:
                    recommendations.append({
                        "test": StatisticalTestType.ONE_WAY_ANOVA.value,
                        "description": "One-way ANOVA",
                        "assumptions": ["Normal distribution", "Equal variances", "Independent observations"],
                        "alternative": StatisticalTestType.KRUSKAL_WALLIS.value,
                        "priority": "primary"
                    })
                else:
                    recommendations.append({
                        "test": StatisticalTestType.TWO_WAY_ANOVA.value,
                        "description": "Two-way ANOVA",
                        "assumptions": ["Normal distribution", "Equal variances", "Independent observations"],
                        "alternative": "Mixed-effects model",
                        "priority": "primary"
                    })
            
            # Correlation analysis if multiple continuous variables
            if dv_count > 1:
                recommendations.append({
                    "test": StatisticalTestType.PEARSON_CORRELATION.value,
                    "description": "Pearson correlation analysis",
                    "assumptions": ["Bivariate normality", "Linear relationship"],
                    "alternative": StatisticalTestType.SPEARMAN_CORRELATION.value,
                    "priority": "secondary"
                })
            
            # Add descriptive statistics recommendation
            recommendations.append({
                "test": "descriptive_statistics",
                "description": "Descriptive statistics and data visualization",
                "assumptions": ["None"],
                "alternative": "Robust statistics",
                "priority": "essential"
            })
            
            # Add normality testing recommendation
            recommendations.append({
                "test": "normality_tests",
                "description": "Shapiro-Wilk or Kolmogorov-Smirnov tests",
                "assumptions": ["None"],
                "alternative": "Q-Q plots",
                "priority": "diagnostic"
            })
            
            self.logger.info(f"Generated {len(recommendations)} statistical test recommendations")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Statistical test recommendation failed: {str(e)}")
            return self._get_fallback_test_recommendations()
    
    def estimate_effect_size(
        self,
        test_type: StatisticalTestType,
        pilot_data: Optional[Dict[str, Any]] = None,
        literature_values: Optional[Dict[str, Any]] = None,
        practical_significance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Estimate effect size based on available information.
        
        Args:
            test_type: Type of statistical test
            pilot_data: Pilot study data if available
            literature_values: Literature-based estimates
            practical_significance: Minimum practically significant difference
            
        Returns:
            Effect size estimates and recommendations
        """
        try:
            effect_size_info = {
                "recommended_effect_size": 0.5,  # Default medium effect
                "effect_size_category": "medium",
                "confidence": "low",
                "basis": "default_assumption",
                "alternatives": {
                    "small": 0.2,
                    "medium": 0.5,
                    "large": 0.8
                }
            }
            
            # Use pilot data if available
            if pilot_data:
                effect_size_info.update(self._calculate_effect_size_from_pilot(test_type, pilot_data))
                effect_size_info["confidence"] = "high"
                effect_size_info["basis"] = "pilot_data"
            
            # Use literature values if available
            elif literature_values:
                effect_size_info.update(self._estimate_from_literature(test_type, literature_values))
                effect_size_info["confidence"] = "medium"
                effect_size_info["basis"] = "literature"
            
            # Use practical significance if specified
            elif practical_significance:
                effect_size_info["recommended_effect_size"] = practical_significance
                effect_size_info["effect_size_category"] = self._categorize_effect_size(
                    practical_significance, test_type
                )
                effect_size_info["confidence"] = "medium"
                effect_size_info["basis"] = "practical_significance"
            
            return effect_size_info
            
        except Exception as e:
            self.logger.error(f"Effect size estimation failed: {str(e)}")
            return {
                "recommended_effect_size": 0.5,
                "effect_size_category": "medium",
                "confidence": "low",
                "basis": "fallback_default"
            }
    
    def validate_experimental_design(self, experimental_design: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate experimental design for statistical analysis.
        
        Args:
            experimental_design: Complete experimental design
            
        Returns:
            Validation results and recommendations
        """
        validation_results = {
            "is_valid": True,
            "issues": [],
            "recommendations": [],
            "statistical_power": "unknown",
            "sample_size_adequate": "unknown"
        }
        
        try:
            # Extract design components
            groups = experimental_design.get('experimental_groups', []) + \
                    experimental_design.get('control_groups', [])
            sample_size = experimental_design.get('sample_size', {})
            variables = experimental_design.get('independent_variables', []) + \
                       experimental_design.get('dependent_variables', [])
            
            # Validate basic design elements
            if len(groups) < 2:
                validation_results["is_valid"] = False
                validation_results["issues"].append("Need at least 2 groups for statistical comparison")
            
            if not variables:
                validation_results["is_valid"] = False
                validation_results["issues"].append("No variables defined for statistical analysis")
            
            # Validate sample size
            if not sample_size:
                validation_results["issues"].append("Sample size not specified")
                validation_results["recommendations"].append("Perform power analysis to determine adequate sample size")
            else:
                # Check if power analysis was performed
                power_analysis = sample_size.get('power_analysis', {})
                if power_analysis:
                    power = power_analysis.get('power', 0)
                    validation_results["statistical_power"] = power
                    
                    if power < 0.8:
                        validation_results["recommendations"].append("Consider increasing sample size for adequate power (≥80%)")
                    
                    required_n = power_analysis.get('required_sample_size', 0)
                    current_n = sample_size.get('biological_replicates', 0)
                    
                    if current_n < required_n:
                        validation_results["sample_size_adequate"] = False
                        validation_results["recommendations"].append(
                            f"Increase sample size to {required_n} per group for adequate power"
                        )
                    else:
                        validation_results["sample_size_adequate"] = True
            
            # Add general recommendations
            validation_results["recommendations"].extend([
                "Verify assumptions of chosen statistical tests",
                "Plan for handling missing data",
                "Consider multiple comparison corrections if needed"
            ])
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Design validation failed: {str(e)}")
            validation_results["is_valid"] = False
            validation_results["issues"].append(f"Validation error: {str(e)}")
            return validation_results
    
    # Private helper methods
    
    def _power_ttest_two_sample(
        self, 
        effect_size: float, 
        sample_size: Optional[int], 
        power: Optional[float], 
        alpha: float
    ) -> PowerAnalysisResult:
        """Calculate power analysis for two-sample t-test."""
        if self.has_statsmodels:
            if sample_size is None:
                # Calculate sample size for given power
                sample_size = int(math.ceil(smp.ttest_power(
                    effect_size=effect_size, 
                    power=power, 
                    alpha=alpha
                )))
                power = power or 0.8
            else:
                # Calculate power for given sample size
                power = smp.ttest_power(
                    effect_size=effect_size, 
                    nobs=sample_size, 
                    alpha=alpha
                )
        else:
            # Fallback calculation
            if sample_size is None:
                sample_size = self._calculate_sample_size_basic(effect_size, power or 0.8, alpha)
                power = power or 0.8
            else:
                power = self._calculate_power_basic(effect_size, sample_size, alpha)
        
        return PowerAnalysisResult(
            test_type=StatisticalTestType.TWO_SAMPLE_TTEST,
            effect_size=effect_size,
            sample_size=max(sample_size, 3),  # Minimum 3 per group
            power=power,
            alpha=alpha,
            groups=2,
            effect_size_category="",
            recommendations=[],
            assumptions=[],
            alternative_tests=[]
        )
    
    def _power_anova_one_way(
        self, 
        effect_size: float, 
        sample_size: Optional[int], 
        power: Optional[float], 
        alpha: float, 
        groups: int
    ) -> PowerAnalysisResult:
        """Calculate power analysis for one-way ANOVA."""
        if self.has_statsmodels:
            try:
                if sample_size is None:
                    # Calculate sample size for given power
                    sample_size = int(math.ceil(smp.ftest_power(
                        effect_size=effect_size, 
                        power=power, 
                        alpha=alpha,
                        df_num=groups-1,
                        df_denom=None
                    )))
                    power = power or 0.8
                else:
                    # Calculate power for given sample size
                    power = smp.ftest_power(
                        effect_size=effect_size, 
                        df_num=groups-1,
                        df_denom=groups*(sample_size-1),
                        alpha=alpha
                    )
            except:
                # Fallback if statsmodels fails
                if sample_size is None:
                    sample_size = self._calculate_sample_size_basic(effect_size, power or 0.8, alpha)
                    power = power or 0.8
                else:
                    power = self._calculate_power_basic(effect_size, sample_size, alpha)
        else:
            # Basic fallback
            if sample_size is None:
                sample_size = self._calculate_sample_size_basic(effect_size, power or 0.8, alpha)
                power = power or 0.8
            else:
                power = self._calculate_power_basic(effect_size, sample_size, alpha)
        
        return PowerAnalysisResult(
            test_type=StatisticalTestType.ONE_WAY_ANOVA,
            effect_size=effect_size,
            sample_size=max(sample_size, 3),
            power=power,
            alpha=alpha,
            groups=groups,
            effect_size_category="",
            recommendations=[],
            assumptions=[],
            alternative_tests=[]
        )
    
    def _power_ttest_paired(
        self, 
        effect_size: float, 
        sample_size: Optional[int], 
        power: Optional[float], 
        alpha: float
    ) -> PowerAnalysisResult:
        """Calculate power analysis for paired t-test."""
        # Paired t-test uses similar calculation to one-sample t-test
        if self.has_statsmodels:
            if sample_size is None:
                sample_size = int(math.ceil(smp.ttest_power(
                    effect_size=effect_size, 
                    power=power, 
                    alpha=alpha
                )))
                power = power or 0.8
            else:
                power = smp.ttest_power(
                    effect_size=effect_size, 
                    nobs=sample_size, 
                    alpha=alpha
                )
        else:
            if sample_size is None:
                sample_size = self._calculate_sample_size_basic(effect_size, power or 0.8, alpha)
                power = power or 0.8
            else:
                power = self._calculate_power_basic(effect_size, sample_size, alpha)
        
        return PowerAnalysisResult(
            test_type=StatisticalTestType.PAIRED_TTEST,
            effect_size=effect_size,
            sample_size=max(sample_size, 3),
            power=power,
            alpha=alpha,
            groups=1,
            effect_size_category="",
            recommendations=[],
            assumptions=[],
            alternative_tests=[]
        )
    
    def _power_chi_square(
        self, 
        effect_size: float, 
        sample_size: Optional[int], 
        power: Optional[float], 
        alpha: float,
        **kwargs
    ) -> PowerAnalysisResult:
        """Calculate power analysis for chi-square test."""
        # Basic chi-square power calculation
        if sample_size is None:
            # Rough estimate for chi-square
            sample_size = int(math.ceil(20 / (effect_size ** 2)))
            power = power or 0.8
        else:
            # Approximate power calculation
            power = min(0.95, 0.5 + (sample_size * effect_size ** 2) / 20)
        
        return PowerAnalysisResult(
            test_type=StatisticalTestType.CHI_SQUARE,
            effect_size=effect_size,
            sample_size=max(sample_size, 30),  # Minimum for chi-square
            power=power,
            alpha=alpha,
            groups=2,
            effect_size_category="",
            recommendations=[],
            assumptions=[],
            alternative_tests=[]
        )
    
    def _power_correlation(
        self, 
        effect_size: float, 
        sample_size: Optional[int], 
        power: Optional[float], 
        alpha: float
    ) -> PowerAnalysisResult:
        """Calculate power analysis for correlation."""
        if sample_size is None:
            # Fisher's z-transformation for correlation
            z_alpha = 1.96 if alpha == 0.05 else stats.norm.ppf(1 - alpha/2) if stats else 1.96
            z_beta = 0.84 if power == 0.8 else stats.norm.ppf(power) if stats else 0.84
            
            # Cohen's approximation for correlation
            sample_size = int(math.ceil(((z_alpha + z_beta) / (0.5 * math.log((1 + effect_size) / (1 - effect_size)))) ** 2 + 3))
            power = power or 0.8
        else:
            # Approximate power calculation for correlation
            z_r = 0.5 * math.log((1 + effect_size) / (1 - effect_size))
            z_score = z_r * math.sqrt(sample_size - 3)
            power = 1 - stats.norm.cdf(1.96 - z_score) if stats else 0.8
        
        return PowerAnalysisResult(
            test_type=StatisticalTestType.PEARSON_CORRELATION,
            effect_size=effect_size,
            sample_size=max(sample_size, 10),
            power=power,
            alpha=alpha,
            groups=1,
            effect_size_category="",
            recommendations=[],
            assumptions=[],
            alternative_tests=[]
        )
    
    def _calculate_sample_size_basic(self, effect_size: float, power: float, alpha: float) -> int:
        """Basic sample size calculation using normal approximation."""
        # Standard normal quantiles
        z_alpha = 1.96 if alpha == 0.05 else 2.58 if alpha == 0.01 else 1.64
        z_beta = 0.84 if power == 0.8 else 1.28 if power == 0.9 else 0.67
        
        # Cohen's formula for two-sample t-test
        n = 2 * ((z_alpha + z_beta) / effect_size) ** 2
        return max(int(math.ceil(n)), 3)
    
    def _calculate_power_basic(self, effect_size: float, sample_size: int, alpha: float) -> float:
        """Basic power calculation using normal approximation."""
        z_alpha = 1.96 if alpha == 0.05 else 2.58 if alpha == 0.01 else 1.64
        z_score = effect_size * math.sqrt(sample_size / 2)
        
        # Power = P(Z > z_alpha - z_score)
        power = 1 - (0.5 * (1 + math.erf((z_alpha - z_score) / math.sqrt(2))))
        return min(max(power, 0.05), 0.95)
    
    def _categorize_effect_size(self, effect_size: float, test_type: StatisticalTestType) -> str:
        """Categorize effect size based on Cohen's conventions."""
        if test_type in [StatisticalTestType.TWO_SAMPLE_TTEST, StatisticalTestType.PAIRED_TTEST]:
            # Cohen's d
            if effect_size < 0.2:
                return "very_small"
            elif effect_size < 0.5:
                return "small"
            elif effect_size < 0.8:
                return "medium"
            else:
                return "large"
        elif test_type == StatisticalTestType.ONE_WAY_ANOVA:
            # Cohen's f
            if effect_size < 0.1:
                return "very_small"
            elif effect_size < 0.25:
                return "small"
            elif effect_size < 0.4:
                return "medium"
            else:
                return "large"
        elif test_type == StatisticalTestType.PEARSON_CORRELATION:
            # Correlation coefficient
            if abs(effect_size) < 0.1:
                return "very_small"
            elif abs(effect_size) < 0.3:
                return "small"
            elif abs(effect_size) < 0.5:
                return "medium"
            else:
                return "large"
        else:
            # Default categorization
            if effect_size < 0.2:
                return "small"
            elif effect_size < 0.5:
                return "medium"
            else:
                return "large"
    
    def _generate_recommendations(self, result: PowerAnalysisResult) -> List[str]:
        """Generate recommendations based on power analysis results."""
        recommendations = []
        
        if result.power < 0.8:
            recommendations.append(f"Consider increasing sample size to achieve 80% power (current: {result.power:.1%})")
        
        if result.sample_size < 10:
            recommendations.append("Very small sample size may limit generalizability")
        
        if result.effect_size < 0.2:
            recommendations.append("Small effect size may require large sample size or more sensitive measures")
        
        if result.effect_size > 1.0:
            recommendations.append("Large effect size suggests robust differences - consider if realistic")
        
        return recommendations
    
    def _get_test_assumptions(self, test_type: StatisticalTestType) -> List[str]:
        """Get assumptions for statistical test."""
        assumptions = {
            StatisticalTestType.TWO_SAMPLE_TTEST: [
                "Normal distribution in both groups",
                "Equal variances (homoscedasticity)",
                "Independent observations"
            ],
            StatisticalTestType.ONE_WAY_ANOVA: [
                "Normal distribution in all groups",
                "Equal variances across groups",
                "Independent observations"
            ],
            StatisticalTestType.PAIRED_TTEST: [
                "Normal distribution of differences",
                "Independent pairs"
            ],
            StatisticalTestType.CHI_SQUARE: [
                "Expected frequencies ≥ 5 in each cell",
                "Independent observations",
                "Mutually exclusive categories"
            ],
            StatisticalTestType.PEARSON_CORRELATION: [
                "Bivariate normal distribution",
                "Linear relationship",
                "Independent observations"
            ]
        }
        
        return assumptions.get(test_type, ["Check specific test assumptions"])
    
    def _suggest_alternative_tests(self, test_type: StatisticalTestType) -> List[str]:
        """Suggest alternative tests."""
        alternatives = {
            StatisticalTestType.TWO_SAMPLE_TTEST: ["Mann-Whitney U test", "Welch's t-test"],
            StatisticalTestType.ONE_WAY_ANOVA: ["Kruskal-Wallis test", "Welch's ANOVA"],
            StatisticalTestType.PAIRED_TTEST: ["Wilcoxon signed-rank test"],
            StatisticalTestType.CHI_SQUARE: ["Fisher's exact test", "G-test"],
            StatisticalTestType.PEARSON_CORRELATION: ["Spearman correlation", "Kendall's tau"]
        }
        
        return alternatives.get(test_type, ["Consult statistical references"])
    
    def _generate_practical_considerations(
        self, 
        sample_size: int, 
        groups: int, 
        test_type: StatisticalTestType
    ) -> List[str]:
        """Generate practical considerations for sample size."""
        considerations = []
        
        total_sample = sample_size * groups
        
        if total_sample > 100:
            considerations.append("Large sample size may increase costs and time requirements")
        
        if total_sample < 30:
            considerations.append("Small sample size may limit statistical power and generalizability")
        
        if groups > 4:
            considerations.append("Multiple groups may require correction for multiple comparisons")
        
        considerations.extend([
            "Consider attrition rates and plan for dropouts",
            "Ensure adequate resources for data collection",
            "Plan for quality control and data validation"
        ])
        
        return considerations
    
    def _calculate_effect_size_from_pilot(
        self, 
        test_type: StatisticalTestType, 
        pilot_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate effect size from pilot data."""
        # Simplified implementation - would need actual pilot data processing
        mean_diff = pilot_data.get('mean_difference', 0)
        pooled_sd = pilot_data.get('pooled_sd', 1)
        
        if pooled_sd > 0:
            cohens_d = mean_diff / pooled_sd
            return {
                "recommended_effect_size": abs(cohens_d),
                "effect_size_category": self._categorize_effect_size(abs(cohens_d), test_type)
            }
        
        return {"recommended_effect_size": 0.5, "effect_size_category": "medium"}
    
    def _estimate_from_literature(
        self, 
        test_type: StatisticalTestType, 
        literature_values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Estimate effect size from literature values."""
        # Simplified implementation
        reported_effect = literature_values.get('effect_size', 0.5)
        
        return {
            "recommended_effect_size": reported_effect,
            "effect_size_category": self._categorize_effect_size(reported_effect, test_type)
        }
    
    def _create_fallback_power_result(
        self, 
        test_type: StatisticalTestType, 
        effect_size: float, 
        alpha: float
    ) -> PowerAnalysisResult:
        """Create fallback power analysis result."""
        return PowerAnalysisResult(
            test_type=test_type,
            effect_size=effect_size,
            sample_size=20,  # Conservative default
            power=0.8,
            alpha=alpha,
            groups=2,
            effect_size_category="medium",
            recommendations=["Verify calculations with statistical software"],
            assumptions=["Check specific test assumptions"],
            alternative_tests=["Consult statistical references"]
        )
    
    def _create_fallback_sample_size_result(
        self, 
        test_type: StatisticalTestType, 
        effect_size: float, 
        power: float, 
        alpha: float
    ) -> SampleSizeResult:
        """Create fallback sample size result."""
        return SampleSizeResult(
            required_sample_size=20,
            total_sample_size=40,
            power_achieved=power,
            effect_size=effect_size,
            alpha=alpha,
            test_type=test_type,
            practical_considerations=["Verify calculations with statistical software"]
        )
    
    def _get_fallback_test_recommendations(self) -> List[Dict[str, Any]]:
        """Get fallback test recommendations."""
        return [
            {
                "test": "two_sample_ttest",
                "description": "Two-sample t-test",
                "assumptions": ["Normal distribution", "Equal variances"],
                "alternative": "Mann-Whitney U test",
                "priority": "primary"
            },
            {
                "test": "descriptive_statistics",
                "description": "Descriptive statistics",
                "assumptions": ["None"],
                "alternative": "Robust statistics",
                "priority": "essential"
            }
        ]


# Convenience functions for quick calculations

def calculate_sample_size_ttest(
    effect_size: float, 
    power: float = 0.8, 
    alpha: float = 0.05
) -> int:
    """
    Quick sample size calculation for two-sample t-test.
    
    Args:
        effect_size: Cohen's d effect size
        power: Desired statistical power
        alpha: Significance level
        
    Returns:
        Required sample size per group
    """
    calculator = StatisticalCalculator()
    result = calculator.calculate_sample_size(
        StatisticalTestType.TWO_SAMPLE_TTEST,
        effect_size=effect_size,
        power=power,
        alpha=alpha
    )
    return result.required_sample_size


def calculate_power_ttest(
    effect_size: float, 
    sample_size: int, 
    alpha: float = 0.05
) -> float:
    """
    Quick power calculation for two-sample t-test.
    
    Args:
        effect_size: Cohen's d effect size
        sample_size: Sample size per group
        alpha: Significance level
        
    Returns:
        Statistical power
    """
    calculator = StatisticalCalculator()
    result = calculator.calculate_power_analysis(
        StatisticalTestType.TWO_SAMPLE_TTEST,
        effect_size=effect_size,
        sample_size=sample_size,
        alpha=alpha
    )
    return result.power


def recommend_tests_for_design(experimental_design: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Quick test recommendations for experimental design.
    
    Args:
        experimental_design: Experimental design dictionary
        
    Returns:
        List of recommended statistical tests
    """
    calculator = StatisticalCalculator()
    
    # Extract variables from design
    independent_vars = experimental_design.get('independent_variables', [])
    dependent_vars = experimental_design.get('dependent_variables', [])
    experimental_groups = experimental_design.get('experimental_groups', [])
    
    return calculator.recommend_statistical_test(
        independent_vars, dependent_vars, experimental_groups
    )


def validate_design_power(experimental_design: Dict[str, Any]) -> Dict[str, Any]:
    """
    Quick validation of experimental design power.
    
    Args:
        experimental_design: Complete experimental design
        
    Returns:
        Validation results
    """
    calculator = StatisticalCalculator()
    return calculator.validate_experimental_design(experimental_design) 