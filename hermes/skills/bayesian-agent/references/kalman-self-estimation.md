# Kalman Self-Estimation — 能力自估计

> ch11 卡尔曼滤波: 预测+修正 + K增益，能力自估计；新反馈按可信度加权融合

## 状态向量

```
x = [前端能力, 后端能力, DevOps能力, 数据分析能力, 设计能力, ...]

每个维度: 0-1 置信度分数
```

## 预测步骤

```
x̂(t|t-1) = F × x(t-1) + B × u(t)

F = 状态转移矩阵（对角阵，通常 = I，能力缓慢变化）
u(t) = 控制输入（主动学习新技能带来的能力提升）
B = 控制矩阵

P̂(t|t-1) = F × P(t-1) × F^T + Q

P = 估计误差协方差
Q = 过程噪声（能力自然波动）
```

## 修正步骤

```
K = P̂ × H^T × (H × P̂ × H^T + R)^(-1)

K = 卡尔曼增益
H = 观测矩阵（从任务结果映射到能力维度）
R = 观测噪声（任务结果的随机性）

x(t) = x̂ + K × (z(t) - H × x̂)

z(t) = 实际观测（任务成功=1, 失败=0）

P(t) = (I - K × H) × P̂
```

## 简化实现

由于 Agent 能力维度多但观测少，使用对角简化：

```python
def kalman_update(ability, uncertainty, observation, observation_noise=0.1):
    """
    ability: 当前能力估计 (0-1)
    uncertainty: 当前不确定性 (0-1)
    observation: 观测值 (1=成功, 0=失败)
    """
    # 预测
    predicted_ability = ability
    predicted_uncertainty = uncertainty + 0.01  # 过程噪声
    
    # 卡尔曼增益
    K = predicted_uncertainty / (predicted_uncertainty + observation_noise)
    
    # 修正
    new_ability = predicted_ability + K * (observation - predicted_ability)
    new_uncertainty = (1 - K) * predicted_uncertainty
    
    return new_ability, new_uncertainty
```

## 能力报告

每周输出: "擅长领域 top-3" + "待提升领域 top-3"
用于: skill 选择建议、任务分配决策
