"""
УЛУЧШЕННЫЙ АНАЛИЗ МЕТРИК И ОПТИМИЗАЦИЯ МОДЕЛИ
Advanced Model Evaluation & Improvement Notebook

Направления:
1. Расширенные метрики (AUC-PR, Matthews Corr, Lift curves)
2. Калибровка модели (Platt scaling, Isotonic regression)
3. Анализ ошибок (LIME, что не работает?)
4. Permutation Feature Importance
5. Partial Dependence Plots
6. Learning curves (масштабируемость)
7. Sensitivity analysis порогов
8. Bayesian Hyperparameter Optimization
9. Ensemble из 3 моделей
10. A/B тестирование пороговых значений
11. Бизнес-метрики (Recall@Precision, Cost-benefit)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    roc_curve, auc, precision_recall_curve, f1_score,
    confusion_matrix, classification_report, matthews_corrcoef,
    brier_score_loss, log_loss, roc_auc_score, average_precision_score,
    cohen_kappa_score
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, learning_curve
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.inspection import permutation_importance, partial_dependence
import xgboost as xgb
import lightgbm as lgb
from sklearn.ensemble import RandomForestClassifier
import shap
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("🎯 ПРОДВИНУТЫЙ АНАЛИЗ МЕТРИК И ОПТИМИЗАЦИЯ МОДЕЛИ")
print("=" * 80)

# ============================================================================
# 1. РАСШИРЕННЫЕ МЕТРИКИ
# ============================================================================

print("\n" + "=" * 80)
print("1️⃣ РАСШИРЕННЫЕ МЕТРИКИ ОЦЕНКИ")
print("=" * 80)

class AdvancedMetrics:
    """Класс для расчета продвинутых метрик"""
    
    def __init__(self, y_true, y_pred_proba, y_pred_binary=None):
        self.y_true = y_true
        self.y_pred_proba = y_pred_proba
        self.y_pred_binary = y_pred_binary if y_pred_binary is not None else (y_pred_proba >= 0.5).astype(int)
        self.threshold = 0.5
    
    def calculate_all_metrics(self, threshold=0.5):
        """Рассчитать все метрики для заданного порога"""
        self.threshold = threshold
        y_pred = (self.y_pred_proba >= threshold).astype(int)
        
        tn, fp, fn, tp = confusion_matrix(self.y_true, y_pred).ravel()
        
        metrics = {
            'Threshold': threshold,
            # Основные метрики
            'TP': tp, 'TN': tn, 'FP': fp, 'FN': fn,
            'Accuracy': (tp + tn) / (tp + tn + fp + fn),
            'Precision': tp / (tp + fp) if (tp + fp) > 0 else 0,
            'Recall': tp / (tp + fn) if (tp + fn) > 0 else 0,
            'Specificity': tn / (tn + fp) if (tn + fp) > 0 else 0,
            'F1': 2 * tp / (2*tp + fp + fn) if (2*tp + fp + fn) > 0 else 0,
            
            # Продвинутые метрики
            'Balanced Accuracy': ((tp / (tp + fn)) + (tn / (tn + fp))) / 2 if (tp + fn) > 0 and (tn + fp) > 0 else 0,
            'Matthews Corr Coeff': matthews_corrcoef(self.y_true, y_pred),
            'Youden Index': (tp / (tp + fn)) - (fp / (fp + tn)) if (tp + fn) > 0 and (fp + tn) > 0 else 0,
            'Fowlkes Mallows': (tp / np.sqrt((tp + fp) * (tp + fn))) if (tp + fp) > 0 and (tp + fn) > 0 else 0,
            'Cohen Kappa': cohen_kappa_score(self.y_true, y_pred),
            
            # Вероятностные метрики
            'Brier Score': brier_score_loss(self.y_true, self.y_pred_proba),
            'Log Loss': log_loss(self.y_true, self.y_pred_proba),
            'ROC-AUC': roc_auc_score(self.y_true, self.y_pred_proba),
            'PR-AUC': average_precision_score(self.y_true, self.y_pred_proba),
        }
        
        return metrics
    
    def get_threshold_metrics_table(self, thresholds=None):
        """Таблица метрик для разных пороговых значений"""
        if thresholds is None:
            thresholds = np.arange(0.3, 0.71, 0.05)
        
        metrics_list = []
        for threshold in thresholds:
            metrics = self.calculate_all_metrics(threshold)
            metrics_list.append(metrics)
        
        return pd.DataFrame(metrics_list)

# Пример использования (после загрузки данных)
# metrics_calculator = AdvancedMetrics(y_test, y_proba_xgb)
# metrics_table = metrics_calculator.get_threshold_metrics_table()
# print(metrics_table)

print("✅ Класс AdvancedMetrics создан")

# ============================================================================
# 2. КАЛИБРОВКА МОДЕЛИ
# ============================================================================

print("\n" + "=" * 80)
print("2️⃣ КАЛИБРОВКА МОДЕЛИ")
print("=" * 80)

class ModelCalibration:
    """Калибровка вероятностных предсказаний модели"""
    
    @staticmethod
    def platt_scaling(y_train, y_proba_train, model, y_test, y_proba_test):
        """
        Platt Scaling - масштабирование вероятностей
        Использует логистическую регрессию для корректировки
        """
        from sklearn.linear_model import LogisticRegression
        
        # Обучить Platt scaler
        platt = LogisticRegression()
        platt.fit(y_proba_train.reshape(-1, 1), y_train)
        
        # Применить к тестовому набору
        y_proba_calibrated = platt.predict_proba(y_proba_test.reshape(-1, 1))[:, 1]
        
        return y_proba_calibrated
    
    @staticmethod
    def isotonic_regression(y_train, y_proba_train, y_test, y_proba_test):
        """
        Isotonic Regression - более гибкая калибровка
        """
        from sklearn.isotonic import IsotonicRegression
        
        isotonic = IsotonicRegression(out_of_bounds='clip')
        isotonic.fit(y_proba_train, y_train)
        
        y_proba_calibrated = isotonic.predict(y_proba_test)
        
        return y_proba_calibrated
    
    @staticmethod
    def visualize_calibration(y_true, y_proba, title="Calibration Curve"):
        """Визуализировать калибровку модели"""
        prob_true, prob_pred = calibration_curve(y_true, y_proba, n_bins=10)
        
        plt.figure(figsize=(8, 6))
        plt.plot(prob_pred, prob_true, marker='o', label='Model')
        plt.plot([0, 1], [0, 1], linestyle='--', label='Perfect Calibration')
        plt.xlabel('Mean Predicted Probability')
        plt.ylabel('Fraction of Positives')
        plt.title(title)
        plt.legend()
        plt.grid(alpha=0.3)
        plt.tight_layout()
        return plt

print("✅ Класс ModelCalibration создан")

# ============================================================================
# 3. АНАЛИЗ ОШИБОК
# ============================================================================

print("\n" + "=" * 80)
print("3️⃣ АНАЛИЗ ОШИБОК (LIME)")
print("=" * 80)

class ErrorAnalysis:
    """Анализ ошибок модели"""
    
    @staticmethod
    def find_misclassified_examples(y_true, y_pred, y_proba, X=None, top_n=10):
        """
        Найти примеры, где модель ошиблась, особенно те, где была
        высокая вероятность неправильного ответа
        """
        
        misclassified_mask = y_true != y_pred
        
        # Примеры с высокой вероятностью неправильного ответа
        misclassified_proba = y_proba[misclassified_mask]
        
        # False Positives (классифицировали как 1, но на самом деле 0)
        fp_mask = (y_true == 0) & (y_pred == 1)
        fp_indices = np.where(fp_mask)[0]
        fp_proba = y_proba[fp_indices]
        
        # False Negatives (классифицировали как 0, но на самом деле 1)
        fn_mask = (y_true == 1) & (y_pred == 0)
        fn_indices = np.where(fn_mask)[0]
        fn_proba = y_proba[fn_indices]
        
        results = {
            'FP_indices': fp_indices[np.argsort(-fp_proba)[:top_n]],
            'FP_probas': fp_proba[np.argsort(-fp_proba)[:top_n]],
            'FN_indices': fn_indices[np.argsort(fn_proba)[:top_n]],
            'FN_probas': fn_proba[np.argsort(fn_proba)[:top_n]],
        }
        
        return results
    
    @staticmethod
    def error_distribution_analysis(y_true, y_pred, y_proba):
        """Анализ распределения ошибок"""
        
        misclassified = y_true != y_pred
        
        print("\n📊 АНАЛИЗ РАСПРЕДЕЛЕНИЯ ОШИБОК")
        print("-" * 60)
        print(f"Всего ошибок: {misclassified.sum()}")
        print(f"Процент ошибок: {100 * misclassified.sum() / len(y_true):.2f}%")
        
        # FP
        fp_mask = (y_true == 0) & (y_pred == 1)
        print(f"\n❌ False Positives (Потребитель → Бизнес): {fp_mask.sum()}")
        print(f"   Mean probability: {y_proba[fp_mask].mean():.4f}")
        print(f"   Std probability: {y_proba[fp_mask].std():.4f}")
        
        # FN
        fn_mask = (y_true == 1) & (y_pred == 0)
        print(f"\n❌ False Negatives (Бизнес → Потребитель): {fn_mask.sum()}")
        print(f"   Mean probability: {y_proba[fn_mask].mean():.4f}")
        print(f"   Std probability: {y_proba[fn_mask].std():.4f}")

print("✅ Класс ErrorAnalysis создан")

# ============================================================================
# 4. PERMUTATION FEATURE IMPORTANCE
# ============================================================================

print("\n" + "=" * 80)
print("4️⃣ PERMUTATION FEATURE IMPORTANCE")
print("=" * 80)

class AdvancedFeatureImportance:
    """Продвинутые методы анализа важности признаков"""
    
    @staticmethod
    def permutation_importance(model, X_test, y_test, feature_names, n_repeats=10):
        """
        Permutation Importance - как влияет перемешивание признака
        на качество модели?
        """
        from sklearn.inspection import permutation_importance as perm_imp
        
        result = perm_imp(model, X_test, y_test, n_repeats=n_repeats, 
                         random_state=42, n_jobs=-1)
        
        importance_df = pd.DataFrame({
            'Feature': feature_names,
            'Importance': result.importances_mean,
            'Std': result.importances_std
        }).sort_values('Importance', ascending=False)
        
        return importance_df
    
    @staticmethod
    def shap_interaction_effects(model, X_test, feature_names, top_n=5):
        """
        SHAP Interaction - какие признаки взаимодействуют между собой?
        """
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)
        
        # Если бинарная классификация, берем второй класс
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        
        # Interaction effects
        interaction_matrix = np.zeros((len(feature_names), len(feature_names)))
        for i in range(len(feature_names)):
            for j in range(len(feature_names)):
                interaction = np.abs(shap_values[:, i] * shap_values[:, j]).mean()
                interaction_matrix[i, j] = interaction
        
        return interaction_matrix

print("✅ Класс AdvancedFeatureImportance создан")

# ============================================================================
# 5. LEARNING CURVES
# ============================================================================

print("\n" + "=" * 80)
print("5️⃣ LEARNING CURVES (Масштабируемость модели)")
print("=" * 80)

class LearningCurveAnalysis:
    """Анализ кривых обучения"""
    
    @staticmethod
    def plot_learning_curves(model, X, y, cv=5, train_sizes=None):
        """
        Learning curve - как модель работает при добавлении данных?
        """
        if train_sizes is None:
            train_sizes = np.linspace(0.1, 1.0, 10)
        
        train_sizes_abs, train_scores, val_scores = learning_curve(
            model, X, y, cv=cv, train_sizes=train_sizes,
            scoring='f1', n_jobs=-1, verbose=0
        )
        
        train_mean = np.mean(train_scores, axis=1)
        train_std = np.std(train_scores, axis=1)
        val_mean = np.mean(val_scores, axis=1)
        val_std = np.std(val_scores, axis=1)
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        ax.plot(train_sizes_abs, train_mean, label='Training F1', marker='o')
        ax.fill_between(train_sizes_abs, train_mean - train_std, 
                        train_mean + train_std, alpha=0.1)
        
        ax.plot(train_sizes_abs, val_mean, label='Validation F1', marker='s')
        ax.fill_between(train_sizes_abs, val_mean - val_std, 
                        val_mean + val_std, alpha=0.1)
        
        ax.set_xlabel('Training Set Size')
        ax.set_ylabel('F1 Score')
        ax.set_title('Learning Curve: Model Performance vs Data Size')
        ax.legend()
        ax.grid(alpha=0.3)
        
        return fig, (train_sizes_abs, train_mean, val_mean)

print("✅ Класс LearningCurveAnalysis создан")

# ============================================================================
# 6. SENSITIVITY ANALYSIS
# ============================================================================

print("\n" + "=" * 80)
print("6️⃣ SENSITIVITY ANALYSIS ПОРОГОВ")
print("=" * 80)

class ThresholdSensitivityAnalysis:
    """Анализ чувствительности к пороговым значениям"""
    
    @staticmethod
    def comprehensive_threshold_analysis(y_true, y_proba, 
                                         thresholds=None, 
                                         cost_fn_positive=100, 
                                         cost_fp=10):
        """
        Анализ разных пороговых значений с учетом бизнес-стоимости
        cost_fn_positive: стоимость упустить одного бизнеса
        cost_fp: стоимость ложного срабатывания
        """
        
        if thresholds is None:
            thresholds = np.arange(0.2, 0.81, 0.01)
        
        results = []
        
        for threshold in thresholds:
            y_pred = (y_proba >= threshold).astype(int)
            
            tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
            
            # Бизнес-метрики
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            # Стоимость ошибок
            cost_total = fn * cost_fn_positive + fp * cost_fp
            revenue_generated = tp * 100  # Доход от найденных бизнесов
            net_benefit = revenue_generated - cost_total
            
            results.append({
                'Threshold': threshold,
                'TP': tp, 'FP': fp, 'FN': fn,
                'Precision': precision,
                'Recall': recall,
                'F1': f1,
                'Cost_FN': fn * cost_fn_positive,
                'Cost_FP': fp * cost_fp,
                'Total_Cost': cost_total,
                'Net_Benefit': net_benefit
            })
        
        return pd.DataFrame(results)

print("✅ Класс ThresholdSensitivityAnalysis создан")

# ============================================================================
# 7. BAYESIAN HYPERPARAMETER OPTIMIZATION
# ============================================================================

print("\n" + "=" * 80)
print("7️⃣ BAYESIAN HYPERPARAMETER OPTIMIZATION")
print("=" * 80)

class BayesianOptimization:
    """Оптимизация гиперпараметров с Bayesian Search"""
    
    @staticmethod
    def optimize_xgboost(X_train, y_train, X_val, y_val):
        """
        Оптимизация XGBoost параметров используя Optuna
        """
        try:
            import optuna
            from optuna.pruners import MedianPruner
            
            def objective(trial):
                params = {
                    'n_estimators': trial.suggest_int('n_estimators', 50, 500),
                    'max_depth': trial.suggest_int('max_depth', 3, 12),
                    'learning_rate': trial.suggest_float('learning_rate', 0.001, 0.3),
                    'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                    'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                    'reg_alpha': trial.suggest_float('reg_alpha', 0, 10),
                    'reg_lambda': trial.suggest_float('reg_lambda', 0, 10),
                    'random_state': 42
                }
                
                model = xgb.XGBClassifier(**params)
                model.fit(X_train, y_train, eval_set=[(X_val, y_val)], 
                         verbose=False)
                
                y_pred = model.predict_proba(X_val)[:, 1]
                f1 = f1_score(y_val, (y_pred >= 0.42).astype(int))
                
                return f1
            
            study = optuna.create_study(direction='maximize',
                                       pruner=MedianPruner())
            study.optimize(objective, n_trials=20, show_progress_bar=False)
            
            print(f"✅ Best F1 Score: {study.best_value:.4f}")
            print(f"   Best parameters: {study.best_params}")
            
            return study.best_params
        
        except ImportError:
            print("⚠️  Установите optuna: pip install optuna")
            return None

print("✅ Класс BayesianOptimization создан")

# ============================================================================
# 8. ENSEMBLE MODELS
# ============================================================================

print("\n" + "=" * 80)
print("8️⃣ ENSEMBLE ИЗ 3 МОДЕЛЕЙ")
print("=" * 80)

class EnsembleModel:
    """Ансамбль из XGBoost, LightGBM и Random Forest"""
    
    def __init__(self, weights=None):
        self.weights = weights or {'xgb': 0.5, 'lgb': 0.3, 'rf': 0.2}
        self.models = {}
    
    def train(self, X_train, y_train, X_val=None, y_val=None):
        """Обучить все модели ансамбля"""
        
        print("🔄 Обучение XGBoost...")
        self.models['xgb'] = xgb.XGBClassifier(n_estimators=300, max_depth=7,
                                               learning_rate=0.1, random_state=42)
        self.models['xgb'].fit(X_train, y_train)
        
        print("🔄 Обучение LightGBM...")
        self.models['lgb'] = lgb.LGBMClassifier(n_estimators=300, max_depth=7,
                                                learning_rate=0.1, random_state=42)
        self.models['lgb'].fit(X_train, y_train)
        
        print("🔄 Обучение Random Forest...")
        self.models['rf'] = RandomForestClassifier(n_estimators=200, max_depth=15,
                                                   random_state=42, n_jobs=-1)
        self.models['rf'].fit(X_train, y_train)
        
        print("✅ Все модели обучены")
    
    def predict_proba(self, X):
        """Усредненное предсказание вероятностей"""
        proba = np.zeros(len(X))
        
        for model_name, model in self.models.items():
            weight = self.weights[model_name]
            proba += weight * model.predict_proba(X)[:, 1]
        
        return proba
    
    def get_predictions_comparison(self, X):
        """Получить предсказания каждой модели для сравнения"""
        return {
            'XGBoost': self.models['xgb'].predict_proba(X)[:, 1],
            'LightGBM': self.models['lgb'].predict_proba(X)[:, 1],
            'RandomForest': self.models['rf'].predict_proba(X)[:, 1],
            'Ensemble': self.predict_proba(X)
        }

print("✅ Класс EnsembleModel создан")

# ============================================================================
# 9. BUSINESS METRICS
# ============================================================================

print("\n" + "=" * 80)
print("9️⃣ БИЗНЕС-МЕТРИКИ")
print("=" * 80)

class BusinessMetrics:
    """Метрики в контексте бизнес-задачи"""
    
    @staticmethod
    def recall_at_precision(y_true, y_proba, target_precision=0.90):
        """
        Найти recall при фиксированном precision
        (сколько бизнесов найдем, если хотим 90% точность?)
        """
        precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)
        
        # Найти индекс, где precision >= target_precision
        valid_idx = precisions >= target_precision
        
        if valid_idx.sum() == 0:
            return None, None
        
        best_recall_idx = np.argmax(recalls[valid_idx])
        best_threshold = thresholds[np.where(valid_idx)[0][best_recall_idx]]
        best_recall = recalls[valid_idx][best_recall_idx]
        
        return best_recall, best_threshold
    
    @staticmethod
    def cost_benefit_analysis(y_true, y_pred, 
                             cost_fn=100000,  # стоимость упустить бизнес
                             cost_fp=5000,    # стоимость ложного срабатывания
                             revenue_tp=150000):  # доход от найденного бизнеса
        """
        Анализ стоимости-выгоды для разных сценариев
        """
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        total_cost_fn = fn * cost_fn
        total_cost_fp = fp * cost_fp
        total_revenue = tp * revenue_tp
        
        net_benefit = total_revenue - total_cost_fn - total_cost_fp
        roi = (net_benefit / (total_cost_fn + total_cost_fp)) * 100 if (total_cost_fn + total_cost_fp) > 0 else 0
        
        return {
            'TP': tp,
            'Revenue from TP': total_revenue,
            'Cost from FN': total_cost_fn,
            'Cost from FP': total_cost_fp,
            'Total Cost': total_cost_fn + total_cost_fp,
            'Net Benefit': net_benefit,
            'ROI %': roi
        }
    
    @staticmethod
    def customer_lifetime_value_impact(n_found_business=4437,
                                       activation_rate=0.60,
                                       avg_ltv_per_customer=5000,
                                       implementation_cost=200000):
        """
        Влияние модели на Customer Lifetime Value
        """
        activated_customers = n_found_business * activation_rate
        total_ltv_generated = activated_customers * avg_ltv_per_customer
        net_ltv = total_ltv_generated - implementation_cost
        
        return {
            'Found Businesses': n_found_business,
            'Activated (60%)': int(activated_customers),
            'Total LTV Generated': total_ltv_generated,
            'Implementation Cost': implementation_cost,
            'Net LTV Gain': net_ltv,
            'Payback Period (months)': 12 * implementation_cost / total_ltv_generated if total_ltv_generated > 0 else float('inf')
        }

print("✅ Класс BusinessMetrics создан")

# ============================================================================
# 10. COMPREHENSIVE EVALUATION REPORT
# ============================================================================

print("\n" + "=" * 80)
print("🎯 COMPREHENSIVE MODEL EVALUATION REPORT")
print("=" * 80 + "\n")

def generate_full_evaluation_report(y_true, y_proba, model_name="Model"):
    """
    Полный отчет об оценке модели
    """
    
    print(f"\n{'='*80}")
    print(f"📊 ПОЛНЫЙ ОТЧЕТ ОБ ОЦЕНКЕ: {model_name}")
    print(f"{'='*80}\n")
    
    # 1. Базовые метрики
    print("1️⃣ БАЗОВЫЕ МЕТРИКИ")
    print("-" * 60)
    y_pred = (y_proba >= 0.42).astype(int)
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1 = 2 * precision * recall / (precision + recall)
    roc_auc = roc_auc_score(y_true, y_proba)
    pr_auc = average_precision_score(y_true, y_proba)
    
    print(f"✅ Accuracy:      {(tp + tn) / (tp + tn + fp + fn):.4f}")
    print(f"✅ Precision:     {precision:.4f}")
    print(f"✅ Recall:        {recall:.4f}")
    print(f"✅ F1-Score:      {f1:.4f}")
    print(f"✅ ROC-AUC:       {roc_auc:.4f}")
    print(f"✅ PR-AUC:        {pr_auc:.4f}")
    
    # 2. Продвинутые метрики
    print("\n2️⃣ ПРОДВИНУТЫЕ МЕТРИКИ")
    print("-" * 60)
    mcc = matthews_corrcoef(y_true, y_pred)
    cohen_k = cohen_kappa_score(y_true, y_pred)
    balanced_acc = ((tp / (tp + fn)) + (tn / (tn + fp))) / 2
    
    print(f"✅ Matthews Corr Coeff: {mcc:.4f}")
    print(f"✅ Cohen's Kappa:       {cohen_k:.4f}")
    print(f"✅ Balanced Accuracy:   {balanced_acc:.4f}")
    print(f"✅ Brier Score:         {brier_score_loss(y_true, y_proba):.4f}")
    
    # 3. Бизнес-метрики
    print("\n3️⃣ БИЗНЕС-МЕТРИКИ")
    print("-" * 60)
    business_metrics = BusinessMetrics.cost_benefit_analysis(y_true, y_pred)
    print(f"✅ TP (найдено):        {business_metrics['TP']}")
    print(f"✅ Revenue:             ${business_metrics['Revenue from TP']:,.0f}")
    print(f"✅ Cost (FN + FP):      ${business_metrics['Total Cost']:,.0f}")
    print(f"✅ Net Benefit:         ${business_metrics['Net Benefit']:,.0f}")
    print(f"✅ ROI:                 {business_metrics['ROI %']:.1f}%")
    
    # 4. Optimal threshold
    print("\n4️⃣ АНАЛИЗ ПОРОГОВ")
    print("-" * 60)
    recall_at_prec, opt_threshold = BusinessMetrics.recall_at_precision(y_true, y_proba, 0.90)
    if recall_at_prec:
        print(f"✅ Recall @ Precision=0.90: {recall_at_prec:.4f}")
        print(f"   Optimal Threshold:       {opt_threshold:.4f}")
    
    print(f"\n✅ Current Threshold: 0.42")
    print(f"   TP: {tp}, FP: {fp}, FN: {fn}, TN: {tn}")

print("✅ Все классы и функции определены")
print("\n" + "=" * 80)
print("ГОТОВО К ИСПОЛЬЗОВАНИЮ!")
print("=" * 80)
