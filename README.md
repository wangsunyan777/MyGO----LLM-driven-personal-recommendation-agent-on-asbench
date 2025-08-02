# MyGO: Multilayer Generator for travel Options

**A recommendation system that categorizes user needs into different types and provides recommendations accordingly. The system identifies three types of user needs when seeking venues: primary needs (core requirements), secondary needs (additional preferences), and potential needs (areas for exploration). Through multi-stage analysis and strategic recommendation ordering, MyGO aims to provide personalized recommendations that satisfy current needs while introducing variety. Among 5 round of valid tests, the agent managed to achieve a highest score of 79.85 on the agentsociety-BehaviorModeling benchmark, showcasing a one-shot prediction accuracy of 0.6 and 5-shot accuracy of 0.78 in the recommendation task and ranking #3 in AgentSociety Challenge 2025, track 1.**

**一个将用户需求分类为不同类型并据此提供推荐的推荐系统。该系统识别用户在寻找场所时的三种需求类型：主要需求（核心要求）、次要需求（额外偏好）和潜在需求（探索领域）。通过多阶段分析和策略性推荐排序，MyGO旨在提供既满足当前需求又引入多样性的个性化推荐。在AgentSociety-BehaviorModeling测试集上，本智能体实现了79.85的综合得分，尤其是0.6的一选命中率和0.78的前五选项命中率，在2025AgentSociety挑战赛赛道一上排名第三。**

## 🌟 Core Concept

MyGO operates on the premise that users have multiple types of preferences when seeking venues. The system categorizes needs as:
- **Primary needs**: Core requirements directly related to the user's current search intent
- **Secondary needs**: Additional services or features that would enhance the experience
- **Potential needs**: New experiences the user might be interested in but hasn't actively considered

**核心概念**

MyGO基于用户在寻找场所时具有多种类型偏好的前提运作。系统将需求分类为：
- **主要需求**：与用户当前搜索意图直接相关的核心要求
- **次要需求**：能够增强体验的额外服务或功能
- **潜在需求**：用户可能感兴趣但尚未主动考虑的新体验

## 🧠 System Architecture

### Four-Stage Processing

**Stage 1: User Analysis**
The system analyzes user review history using natural language processing to:
- Extract writing patterns and preferences
- Identify behavior patterns across venue types
- Classify needs into the three categories
- Create a user profile with preference weightings

**第一阶段：用户分析**
系统使用自然语言处理分析用户评论历史：
- 提取写作模式和偏好
- 识别跨场所类型的行为模式
- 将需求分类为三种类别
- 创建带有偏好权重的用户画像

**Stage 2: Primary Matching**
From the candidate venue pool, the system:
- Uses semantic analysis to match venues with primary needs
- Evaluates venue characteristics beyond category labels
- Selects the top 10 venues most aligned with primary needs

**第二阶段：主要匹配**
从候选场所池中，系统：
- 使用语义分析将场所与主要需求匹配
- 评估超越类别标签的场所特征
- 选择与主要需求最匹配的前10个场所

**Stage 3: Primary Selection Refinement**
The system narrows the 10 candidates to 5 by considering:
- User rating patterns
- Quality preferences
- Geographic convenience
- Diversity within primary options

**第三阶段：主要选择优化**
系统将10个候选缩减为5个，考虑：
- 用户评分模式
- 质量偏好
- 地理便利性
- 主要选项内的多样性

**Stage 4: Diversification**
The system identifies 3 additional venues that match:
- Secondary needs (complementary services)
- Potential needs (exploration opportunities)
- User quality standards

**第四阶段：多样化**
系统识别3个额外场所，匹配：
- 次要需求（补充服务）
- 潜在需求（探索机会）
- 用户质量标准

## 🎯 Recommendation Ordering Strategy

The system uses a specific ordering pattern rather than grouping recommendations by type:

**Final sequence**: Primary-1, Secondary-1, Primary-4, Secondary-2, Primary-5

**Rationale for skipping Primary-2 and Primary-3**:
- Reduces cognitive load from similar options
- Maintains user interest through content variation
- Balances core need satisfaction with exploration
- Aims to prevent choice paralysis

**推荐排序策略**

系统使用特定的排序模式，而不是按类型分组推荐：

**最终序列**：主要-1，次要-1，主要-4，次要-2，主要-5

**跳过主要-2和主要-3的理由**：
- 减少相似选项的认知负荷
- 通过内容变化保持用户兴趣
- 平衡核心需求满足与探索
- 旨在防止选择困难

 ## To run the code, please follow the instructions on https://github.com/tsinghua-fib-lab/AgentSociety/tree/main/packages/agentsociety-benchmark/agentsociety_benchmark/benchmarks/BehaviorModeling.

 ## 为了运行本代码，请按照https://github.com/tsinghua-fib-lab/AgentSociety/tree/main/packages/agentsociety-benchmark/agentsociety_benchmark/benchmarks/BehaviorModeling   的指引配置好您的环境。
