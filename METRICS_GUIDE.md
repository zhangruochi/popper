# 计算生物学助手指标计算指南

本文档详细说明了计算生物学助手（Computational Biologist Copilot）工作流中所有指标的计算公式、值域和意义。

## 目录

1. [基础指标](#基础指标)
2. [结构预测指标](#结构预测指标)
3. [能量评分指标](#能量评分指标)
4. [复合评分指标](#复合评分指标)
5. [辅助指标](#辅助指标)

---

## 基础指标

### 1. Potency Score (potency_score)

**定义**: 预测的肽分子结合活性/效力分数

**计算公式**:

对于最小化目标（如KD值，单位nM，越小越好）：
```
potency_score = 1 / (1 + KD_nM / scale_nm)
```

其中：
- `KD_nM`: 预测的结合解离常数（nM）
- `scale_nm`: 缩放参数，默认值为 1000.0 nM

对于最大化目标（如IC50，单位nM，越大越好）：
```
potency_score = predicted_value  # 直接使用预测值（假设已归一化到0-1）
```

**值域**: `[0, 1]`
- `0`: 无活性或极弱结合
- `1`: 最强结合活性

**意义**:
- 反映肽分子与目标蛋白的结合强度
- 基于机器学习模型（TabularModel）从SMILES结构预测
- 用于评估候选分子的治疗潜力

**代码位置**: `tools.py:normalize_kd_nm_to_potency_score()`

---

### 2. Developability Score (developability_score)

**定义**: 评估肽分子的成药性（可开发性）分数

**计算公式**:
```
developability_score = max(0.0, 1.0 - |net_charge| / 10.0)
```

其中：
- `net_charge`: 净电荷 = (K + R + H) - (D + E)
  - K: 赖氨酸数量
  - R: 精氨酸数量
  - H: 组氨酸数量
  - D: 天冬氨酸数量
  - E: 谷氨酸数量

**值域**: `[0, 1]`
- `0`: 净电荷过高（>10或<-10），成药性差
- `1`: 净电荷接近0，成药性最佳

**意义**:
- 评估肽分子的物理化学性质
- 高净电荷可能导致膜通透性差、溶解度问题
- 用于筛选具有良好药物性质的候选分子

**代码位置**: `nodes/design.py:design_score_candidates()` (line 1367-1368)

---

## 结构预测指标

### 3. Interface Confidence (interface_confidence)

**定义**: 界面预测置信度分数（基于iPTM）

**计算公式**:
```
interface_confidence = iPTM
```

其中 `iPTM` 从结构预测的置信度指标中提取。

**值域**: `[0, 1]`
- `0`: 界面预测不可靠
- `0.5`: 界面预测基本可靠
- `>0.7`: 界面预测可靠
- `1`: 界面预测非常可靠

**意义**:
- 评估预测的蛋白质-肽复合物界面的可靠性
- iPTM (Interface Predicted TM-score) 衡量界面区域的置信度
- 在新的三层分层打分系统中，作为`interface_quality_score`的组成部分（权重30%）

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1252-1255)

---

### 4. Interface Geometry Score (interface_geometry_score)

**定义**: 界面几何质量分数

**计算公式**:
```
interface_geometry_score = average(
    interface_sc,      # 界面分数（归一化到0-1）
    interface_packstat # 界面堆积统计（归一化到0-1）
)
```

其中：
- `interface_sc`: 从能量评分工具返回的界面分数（0-1）
- `interface_packstat`: 从能量评分工具返回的界面堆积统计（0-1）

**值域**: `[0, 1]`
- `0`: 界面几何质量极差
- `0.5`: 界面几何质量中等
- `>0.7`: 界面几何质量良好
- `1`: 界面几何质量最佳

**意义**:
- 评估界面的几何特征（堆积密度、接触质量等）
- 在新的三层分层打分系统中，作为`interface_quality_score`的组成部分（权重40%）

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1293-1305)

---

### 5. Interface Energetics Score (interface_energetics_score)

**定义**: 界面能量学质量分数

**计算公式**:
```
interface_energetics_score = average(
    normalize_binder_score(binder_score),      # Rosetta能量（归一化）
    normalize_interface_dG(interface_dG),     # 结合自由能（归一化）
    normalize_hbonds(interface_hbonds)         # 氢键数量（归一化）
)
```

其中：
- `binder_score`: Rosetta能量分数（REU，越低越好）→ 归一化为0-1（越高越好）
- `interface_dG`: 界面结合自由能（kcal/mol，越低越好）→ 归一化为0-1（越高越好）
- `interface_hbonds`: 界面氢键数量（越多越好）→ 归一化为0-1（越高越好）

**值域**: `[0, 1]`
- `0`: 界面能量学质量极差
- `0.5`: 界面能量学质量中等
- `>0.7`: 界面能量学质量良好
- `1`: 界面能量学质量最佳

**意义**:
- 综合评估界面的能量学特征（结合能量、自由能、氢键相互作用）
- 在新的三层分层打分系统中，作为`interface_quality_score`的组成部分（权重30%）

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1307-1331)

---

### 6. Interface Quality Score (interface_quality_score)

**定义**: 界面质量综合分数（Layer 3 → Layer 2的中间指标）

**计算公式**:
```
interface_quality_score = 
    interface_confidence × 0.30 +
    interface_geometry_score × 0.40 +
    interface_energetics_score × 0.30
```

**值域**: `[0, 1]`

**意义**:
- 综合评估界面的三个维度：置信度、几何质量、能量学质量
- 在分层打分系统中，作为`structural_quality_score`的组成部分（权重60%）

**代码位置**: `tools.py:calculate_composite_score()` (line 616-620)

---

### 7. Backbone Score (backbone_score)

**定义**: 肽分子主链结构质量分数

**计算公式**:
```
# 从complex_plddt计算
plddt_val = complex_plddt

# 如果pLDDT在0-100范围内，归一化到0-1
if plddt_val > 1.5:
    plddt_val = plddt_val / 100.0

# 限制在[0, 1]范围内
backbone_score = max(0.0, min(1.0, plddt_val))
```

其中：
- `complex_plddt`: 复合物的预测局部距离差异测试（Predicted Local Distance Difference Test）分数

**值域**: `[0, 1]`
- `0`: 主链结构质量极差
- `0.5`: 主链结构质量中等
- `>0.7`: 主链结构质量良好
- `>0.9`: 主链结构质量优秀

**意义**:
- 评估肽分子主链结构的预测质量
- pLDDT衡量每个残基的局部结构置信度
- 用于判断整体结构预测的可靠性

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1097-1106)

---

### 8. Confidence Score (confidence_score)

**定义**: 结构预测的整体置信度分数

**计算公式**:
```
confidence_score = confidence_metrics.get("confidence_score")
```

直接从结构预测工具返回的置信度指标中提取。

**值域**: `[0, 1]` 或 `[0, 100]`（取决于工具）
- `0`: 置信度极低
- `>0.7`: 置信度良好
- `>0.9`: 置信度很高

**意义**:
- 结构预测工具提供的整体置信度评估
- 综合了多个结构质量指标

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1084-1085)

---

### 9. iPTM (Interface Predicted TM-score)

**定义**: 界面预测TM分数

**计算公式**:
```
iptm = confidence_metrics.get("iptm")
```

直接从结构预测的置信度指标中提取。

**值域**: `[0, 1]`
- `0`: 界面预测不可靠
- `>0.5`: 界面预测基本可靠
- `>0.7`: 界面预测可靠

**意义**:
- 专门评估蛋白质-肽界面的预测质量
- TM-score衡量两个结构的相似性
- 用于判断界面区域的结构预测可信度

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1086)

---

### 10. Complex pLDDT (complex_plddt)

**定义**: 复合物的预测局部距离差异测试分数

**计算公式**:
```
complex_plddt = confidence_metrics.get("complex_plddt")
```

直接从结构预测的置信度指标中提取。

**值域**: `[0, 100]` 或 `[0, 1]`（取决于工具）
- `0-50`: 结构质量差
- `50-70`: 结构质量中等
- `70-90`: 结构质量良好
- `90-100`: 结构质量优秀

**意义**:
- 评估复合物结构的局部质量
- 每个残基的pLDDT值反映该位置的预测可靠性
- 用于识别结构预测中的不确定区域

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1087)

---

## 能量评分指标

### 归一化函数

在能量评分指标中，有三个关键的归一化函数用于将"越低越好"或"越多越好"的原始指标转换为统一的0-1分数（越高越好）：

#### normalize_binder_score()

**定义**: 将binder_score（REU，越低越好）归一化为0-1分数（越高越好）

**计算公式**:
```
normalized_score = 1 / (1 + binder_score / scale_reu)
```

其中：
- `binder_score`: Rosetta能量分数（REU），观测范围`[60, 485]`
- `scale_reu`: 缩放参数，默认150.0 REU（当binder_score = scale_reu时，score = 0.5）

**示例**:
- `binder_score = 60 REU` → `normalized_score ≈ 0.71`（优秀）
- `binder_score = 150 REU` → `normalized_score = 0.50`（参考值）
- `binder_score = 300 REU` → `normalized_score ≈ 0.33`（较差）

**代码位置**: `tools.py:normalize_binder_score()` (line 60-100)

---

#### normalize_interface_dG()

**定义**: 将interface_dG（kcal/mol，越低越好）归一化为0-1分数（越高越好）

**计算公式**:
```
normalized_score = 1 / (1 + dG / scale_kcal)
```

其中：
- `dG`: 界面结合自由能（kcal/mol），观测范围`[68, 497]`
- `scale_kcal`: 缩放参数，默认100.0 kcal/mol（当dG = scale_kcal时，score = 0.5）

**示例**:
- `dG = 68 kcal/mol` → `normalized_score ≈ 0.60`（优秀）
- `dG = 100 kcal/mol` → `normalized_score = 0.50`（参考值）
- `dG = 250 kcal/mol` → `normalized_score ≈ 0.29`（较差）

**代码位置**: `tools.py:normalize_interface_dG()` (line 103-133)

---

#### normalize_hbonds()

**定义**: 将氢键数量（越多越好）归一化为0-1分数（越高越好）

**计算公式**:
```
normalized_score = min(1.0, hbonds / max_expected)
```

其中：
- `hbonds`: 界面氢键数量（整数，≥0）
- `max_expected`: 预期最大氢键数，默认10

**示例**:
- `hbonds = 0` → `normalized_score = 0.0`
- `hbonds = 5` → `normalized_score = 0.5`（假设max_expected=10）
- `hbonds ≥ 10` → `normalized_score = 1.0`

**代码位置**: `tools.py:normalize_hbonds()` (line 136-152)

---

### 8. Binder Score (binder_score)

**定义**: 结合剂评分，基于Rosetta能量计算

**计算公式**:
```
binder_score = energy_metrics.get("binder_score")
```

从能量评分工具返回的结果中直接提取。

**值域**: 正值（单位：Rosetta能量单位，REU），**越低越好**
- 更低的值表示更强的结合
- 观测范围：`[60, 485]` REU（基于实际运行数据）
- 优秀值：< 100 REU
- 典型值：~150 REU
- 较差值：> 250 REU

**重要提示**: 本工具返回的是正值（而非标准Rosetta的负能量）。在打分系统中，通过`normalize_binder_score()`函数转换为0-1分数（越低的REU → 越高的score）。

**意义**:
- 基于Rosetta能量函数的结合亲和力评估
- 考虑了范德华力、静电相互作用、氢键等
- 用于评估结合强度的物理化学基础
- 在新的分层打分系统中，归一化后作为`interface_energetics_score`的组成部分

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1124-1128)

---

### 11. Energy Score (energy_score)

**定义**: 能量评分的标量总结（向后兼容指标）

**计算公式**:
```
# 优先使用binder_score
energy_score = energy_metrics.get("binder_score") 
              or energy_metrics.get("interface_sc")
              or energy_metrics.get("interface_packstat")
```

从能量评分结果中提取，按优先级选择：
1. `binder_score`（优先）
2. `interface_sc`（备选）
3. `interface_packstat`（备选）

**值域**: 取决于使用的具体指标
- 如果使用`binder_score`: 正值，范围约`[60, 485]` REU（**注意**：本工具返回正值，不是负值）
- 如果使用`interface_sc`或`interface_packstat`: `[0, 1]`

**意义**:
- 能量评分的单一标量表示（向后兼容）
- 用于快速比较不同候选分子的结合能量
- **注意**：在新的分层打分系统中，推荐使用`interface_energetics_score`替代此指标

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1282-1291)

---

### 12. Interface dG (interface_dG)

**定义**: 界面结合自由能

**计算公式**:
```
interface_dG = energy_metrics.get("interface_dG")
```

从能量评分结果中直接提取。

**值域**: 正值（单位：kcal/mol），**越低越好**
- 更低的值表示更有利的结合
- 观测范围：`[68, 497]` kcal/mol（基于实际运行数据）
- 优秀值：< 100 kcal/mol
- 典型值：~150 kcal/mol
- 较差值：> 250 kcal/mol

**重要提示**: 本工具返回的是正值（而非标准热力学ΔG的负值）。在打分系统中，通过`normalize_interface_dG()`函数转换为0-1分数。

**意义**:
- 界面结合的热力学自由能
- 反映结合过程的能量变化
- 用于评估结合的热力学可行性
- 在新的分层打分系统中，归一化后作为`interface_energetics_score`的组成部分

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1118-1120)

---

### 13. Interface Hydrogen Bonds (interface_hbonds)

**定义**: 界面区域的氢键数量

**计算公式**:
```
interface_hbonds = energy_metrics.get("interface_interface_hbonds")
```

从能量评分结果中直接提取。

**值域**: `[0, +∞)`（整数）
- `0`: 无氢键
- `>5`: 多个氢键，界面稳定

**意义**:
- 界面区域的氢键数量
- 氢键是稳定蛋白质-肽复合物的关键因素
- 用于评估界面的相互作用强度

**代码位置**: `tools.py:merge_structure_energy_metrics()` (line 1118-1120)

---

## 复合评分指标

### 14. Final Score (final_score)

**定义**: 加权复合分数，用于最终排名（三层分层架构）

**计算公式**:

系统采用**三层分层架构**计算最终分数：

**Layer 3**: 界面质量子组件
```
interface_quality_score = 
    interface_confidence × 0.30 +
    interface_geometry_score × 0.40 +
    interface_energetics_score × 0.30
```

**Layer 2**: 结构质量
```
structural_quality_score = 
    interface_quality_score × 0.60 +
    backbone_score × 0.40
```

**Layer 1**: 基础分数
```
base_score = 
    potency_score × 0.20 +
    structural_quality_score × 0.60 +
    developability_score × 0.20
```

**默认权重配置** (Layer 1):
- `binding_affinity_weight = 0.20` (20%) - ML预测的potency
- `structural_quality_weight = 0.60` (60%) - 结构质量（包含界面和主链）
- `developability_weight = 0.20` (20%) - 成药性

**Layer 2权重**:
- `interface_vs_backbone_split = 0.60` (60%界面，40%主链)

**Layer 3权重**:
- `interface_confidence_sub = 0.30` (30%置信度)
- `interface_geometry_sub = 0.40` (40%几何质量)
- `interface_energetics_sub = 0.30` (30%能量学)

**有效权重分布**:
| 组件 | 有效权重 | 计算路径 |
|------|----------|----------|
| potency (ML预测) | 20% | 直接 |
| interface_confidence (iPTM) | 10.8% | 0.30 × 0.60 × 0.60 |
| interface_geometry (sc, packstat) | 14.4% | 0.40 × 0.60 × 0.60 |
| interface_energetics (binder, dG, hbonds) | 10.8% | 0.30 × 0.60 × 0.60 |
| backbone (pLDDT) | 24% | 0.40 × 0.60 |
| developability (charge) | 20% | 直接 |
| **总计** | **100%** | ✓ |

**步骤2**: 应用惩罚因子
```
penalty_factor = 1.0

# 主链质量惩罚
if backbone_score < 0.5:
    penalty = 0.2 × (0.5 - backbone_score)  # 最多10%惩罚
    penalty_factor -= penalty

# 净电荷惩罚
if net_charge > 4:
    excess = net_charge - 4
    penalty = 0.05 × excess  # 每个超出电荷5%惩罚
    penalty_factor -= penalty

# 聚集风险惩罚
if aggregation_risk == "high":
    penalty_factor -= 0.15  # 15%惩罚
elif aggregation_risk == "medium":
    penalty_factor -= 0.05  # 5%惩罚

# 确保惩罚因子不低于0.5
penalty_factor = max(0.5, penalty_factor)
```

**步骤3**: 计算最终分数
```
final_score = base_score × penalty_factor
```

**值域**: `[0, 1]`
- `0-0.4`: 低优先级（low_priority）
- `0.4-0.7`: 中等优先级（medium_priority）
- `0.7-1.0`: 高优先级（high_priority）

**意义**:
- 综合评估候选分子的整体质量
- 用于对所有候选分子进行排名
- 考虑多个维度的平衡

**代码位置**: `tools.py:calculate_composite_score()` (line 545-701)

---

### 15. Base Score (base_score)

**定义**: 加权组合的基础分数（应用惩罚前）

**计算公式**: 见 [Final Score](#12-final-score-final_score) 的步骤1

**值域**: `[0, 1]`

**意义**:
- 惩罚前的原始加权分数
- 用于分析各指标的贡献

**代码位置**: `tools.py:calculate_composite_score()` (line 628-633)

---

### 16. Penalty Factor (penalty_factor)

**定义**: 应用于基础分数的惩罚因子

**计算公式**: 见 [Final Score](#12-final-score-final_score) 的步骤2

**值域**: `[0.5, 1.0]`
- `1.0`: 无惩罚
- `<1.0`: 存在惩罚
- `0.5`: 最大惩罚（最低值）

**意义**:
- 反映候选分子在关键指标上的缺陷
- 用于降低有严重问题的候选分子排名

**代码位置**: `tools.py:calculate_composite_score()` (line 635-664)

---

### 15. Score Breakdown (score_breakdown)

**定义**: 各指标对最终分数的贡献分解

**计算公式**:
```
score_breakdown = {
    # Layer 1 contributions
    "binding_affinity_contribution": potency_score × binding_affinity_weight,
    "structural_quality_contribution": structural_quality_score × structural_quality_weight,
    "developability_contribution": developability_score × developability_weight,
    # Layer 2 details
    "interface_quality_score": interface_quality_score,
    "backbone_score": backbone_score,
    # Layer 3 details
    "interface_breakdown": {
        "confidence": interface_confidence,
        "geometry": interface_geometry_score,
        "energetics": interface_energetics_score
    }
}
```

**值域**: 每个贡献值在 `[0, weight]` 范围内

**意义**:
- 显示各指标对最终分数的具体贡献
- 提供三层架构的详细分解
- 用于理解候选分子的优势和劣势
- 帮助优化策略的制定

**代码位置**: `tools.py:calculate_composite_score()` (line 682-700)

---

## 辅助指标

### 16. Net Charge (net_charge)

**定义**: 肽分子的净电荷

**计算公式**:
```
net_charge = count(K) + count(R) + count(H) - count(D) - count(E)
```

其中：
- `K`: 赖氨酸（Lys）
- `R`: 精氨酸（Arg）
- `H`: 组氨酸（His）
- `D`: 天冬氨酸（Asp）
- `E`: 谷氨酸（Glu）

**值域**: 整数，通常范围 `[-20, +20]`

**意义**:
- 影响肽分子的溶解度、膜通透性
- 高正电荷可能导致聚集、细胞毒性
- 用于developability_score的计算和惩罚

**代码位置**: `tools.py:validate_sequence()` (line 303-307)

---

### 17. Potency Uncertainty (potency_uncertainty)

**定义**: 活性预测的不确定性

**计算公式**:
```
potency_uncertainty = prediction_result.get("uncertainty")
```

从机器学习模型的预测结果中直接提取。

**值域**: `[0, +∞)`
- `0`: 完全确定
- `>0.1`: 存在不确定性
- `>0.3`: 不确定性较高

**意义**:
- 反映模型对预测值的置信度
- 用于评估预测结果的可靠性
- 高不确定性可能需要实验验证

**代码位置**: `nodes/design.py:design_score_candidates()` (line 1427-1428)

---

### 18. Predicted Potency (predicted_potency)

**定义**: 原始预测的活性值（未归一化）

**计算公式**:
```
predicted_potency = prediction_result.get("prediction")
```

从机器学习模型的预测结果中直接提取。

**值域**: 取决于模型和训练数据
- 如果预测KD值：通常范围 `[0.1, 100000]` nM
- 如果预测IC50：通常范围 `[0.1, 100000]` nM

**意义**:
- 模型输出的原始预测值
- 用于理解实际的结合强度
- 用于与实验数据对比

**代码位置**: `nodes/design.py:design_score_candidates()` (line 1423-1424)

---

## 指标优先级和权重配置

### 默认权重配置

**Layer 1权重** (顶层):
```python
scoring_weights = {
    "binding_affinity": 0.20,      # 20% - ML预测的potency（从70%降低）
    "structural_quality": 0.60,    # 60% - 结构质量（从25%提升）
    "developability": 0.20          # 20% - 成药性（从5%提升）
}
```

**Layer 2权重** (结构质量细分):
```python
structural_sub_weights = {
    "interface_vs_backbone_split": 0.60  # 60%界面，40%主链
}
```

**Layer 3权重** (界面质量细分):
```python
interface_sub_weights = {
    "interface_confidence_sub": 0.30,    # 30% - iPTM置信度
    "interface_geometry_sub": 0.40,       # 40% - 几何质量（sc, packstat）
    "interface_energetics_sub": 0.30       # 30% - 能量学（binder, dG, hbonds）
}
```

**有效权重分布** (最终贡献):
| 组件 | 有效权重 | 计算路径 |
|------|----------|----------|
| potency (ML预测) | 20% | 直接 |
| interface_confidence (iPTM) | 10.8% | 0.30 × 0.60 × 0.60 |
| interface_geometry (sc, packstat) | 14.4% | 0.40 × 0.60 × 0.60 |
| interface_energetics (binder, dG, hbonds) | 10.8% | 0.30 × 0.60 × 0.60 |
| backbone (pLDDT) | 24% | 0.40 × 0.60 |
| developability (charge) | 20% | 直接 |
| **总计** | **100%** | ✓ |

### 惩罚阈值

- **Backbone Score惩罚**: `backbone_score < 0.5` 时触发
- **净电荷惩罚**: `net_charge > 4` 时触发
- **聚集风险惩罚**: `aggregation_risk == "high"` 或 `"medium"` 时触发

### 优先级分级

- **High Priority (高优先级)**: `final_score >= 0.7`
- **Medium Priority (中等优先级)**: `0.4 <= final_score < 0.7`
- **Low Priority (低优先级)**: `final_score < 0.4`

---

## 指标计算流程

### 完整评分流程

1. **序列验证**: 计算 `net_charge` 和基础属性
2. **SMILES生成**: 将肽序列转换为SMILES表示
3. **活性预测**: 使用ML模型预测 `predicted_potency` 和 `potency_uncertainty`
4. **归一化**: 将 `predicted_potency` 转换为 `potency_score` (0-1)
5. **结构预测** (可选): 计算 `interface_confidence` (iPTM), `backbone_score` (pLDDT), `confidence_score`, `complex_plddt`
6. **能量评分** (可选): 计算 `binder_score`, `interface_dG`, `interface_hbonds`, `interface_sc`, `interface_packstat`
7. **能量归一化**: 
   - 使用 `normalize_binder_score()` 将binder_score归一化
   - 使用 `normalize_interface_dG()` 将interface_dG归一化
   - 使用 `normalize_hbonds()` 将interface_hbonds归一化
8. **指标合并**: 使用 `merge_structure_energy_metrics()` 合并结构/能量指标，计算：
   - `interface_confidence` (从iPTM)
   - `interface_geometry_score` (从interface_sc和interface_packstat平均)
   - `interface_energetics_score` (从归一化后的binder_score, interface_dG, interface_hbonds平均)
   - `backbone_score` (从complex_plddt)
9. **分层打分** (三层架构):
   - **Layer 3**: 计算 `interface_quality_score` = confidence × 0.30 + geometry × 0.40 + energetics × 0.30
   - **Layer 2**: 计算 `structural_quality_score` = interface_quality × 0.60 + backbone × 0.40
   - **Layer 1**: 计算 `base_score` = potency × 0.20 + structural_quality × 0.60 + developability × 0.20
10. **应用惩罚**: 根据backbone_score、net_charge、aggregation_risk计算penalty_factor
11. **最终分数**: `final_score = base_score × penalty_factor`
12. **排名**: 按 `final_score` 降序排列

---

## 注意事项

1. **缺失值处理**:
   - 如果结构预测不可用，`interface_confidence`、`interface_geometry_score`、`interface_energetics_score` 使用默认值0.5
   - 如果能量评分不可用，相关能量指标为 `None` 或 `"N/A"`
   - `backbone_score` 默认值为0.7（如果结构预测不可用）

2. **归一化**:
   - 所有分数最终归一化到 `[0, 1]` 范围以便比较
   - pLDDT值可能需要从 `[0, 100]` 归一化到 `[0, 1]`

3. **权重调整**:
   - 权重可通过配置文件 `computational_biologist_copilot.yaml` 中的 `scoring_weights` 参数调整
   - 支持三层架构的权重配置：
     - Layer 1: `binding_affinity`, `structural_quality`, `developability`
     - Layer 2: `interface_vs_backbone_split`
     - Layer 3: `interface_confidence_sub`, `interface_geometry_sub`, `interface_energetics_sub`
   - 归一化参数可通过 `energy_normalization` 配置调整（scale_reu, scale_kcal, max_expected）
   - 调整权重会影响最终排名

4. **惩罚机制**:
   - 惩罚因子确保有严重缺陷的候选分子不会获得高分
   - 惩罚因子最低为0.5，避免完全排除候选分子

---

## 参考文献

- 代码实现位置：
  - `local_agent/langgraph/workflows/computational_biologist_copilot/tools.py`
  - `local_agent/langgraph/workflows/computational_biologist_copilot/nodes/design.py`
  - `local_agent/langgraph/workflows/computational_biologist_copilot/nodes/evaluation.py`

---

**文档版本**: 2.0  
**最后更新**: 2025-01-03  
**维护者**: Computational Biologist Copilot Team

---

## 更新日志

### 版本 2.0 (2025-01-03)

**重大更新**:
- ✅ 实施三层分层打分架构（Layer 1 → Layer 2 → Layer 3）
- ✅ 权重重新分配：potency 70% → 20%，structural_quality 25% → 50%，developability 5% → 30%
- ✅ 新增三个归一化函数：`normalize_binder_score()`, `normalize_interface_dG()`, `normalize_hbonds()`
- ✅ 界面质量指标分离为三个子组件：`interface_confidence`, `interface_geometry_score`, `interface_energetics_score`
- ✅ 能量指标整合：binder_score、interface_dG、interface_hbonds 纳入 interface_energetics_score
- ✅ 修正文档错误：binder_score和interface_dG的值域描述（从负值修正为正值范围）

**架构改进**:
- 从单一interface_score分离为三层架构，逻辑更清晰
- 能量指标正确归一化（"越低越好" → "越高越好"）
- 提供详细的score_breakdown，包含三层架构的完整分解

