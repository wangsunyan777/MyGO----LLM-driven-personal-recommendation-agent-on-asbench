# MyGO----LLM-driven-personal-recommendation-agent-on-asbench
My entry for UrbanCup 2025, track one. The agent serves as a personalized recommender designed for agentsociety benchmark (based on the yelp datasource) and achieves a one-shot prediction accuracy of sixty percent.

# MyGO: Multilayer Generated Options

**A recommendation system that categorizes user needs into different types and provides recommendations accordingly. The system identifies three types of user needs when seeking venues: primary needs (core requirements), secondary needs (additional preferences), and potential needs (areas for exploration). Through multi-stage analysis and strategic recommendation ordering, MyGO aims to provide personalized recommendations that satisfy current needs while introducing variety.**

**一个将用户需求分类为不同类型并据此提供推荐的推荐系统。该系统识别用户在寻找场所时的三种需求类型：主要需求（核心要求）、次要需求（额外偏好）和潜在需求（探索领域）。通过多阶段分析和策略性推荐排序，MyGO旨在提供既满足当前需求又引入多样性的个性化推荐。**

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

## 🔍 Key Technical Components

### User Mention Detection
- Identifies when user names appear in venue reviews
- Uses tokenization and context analysis
- Provides additional data points for user behavior understanding

**用户提及检测**
- 识别用户姓名何时出现在场所评论中
- 使用分词和上下文分析
- 为用户行为理解提供额外数据点

### Semantic Venue Analysis
- Analyzes venues beyond category classifications
- Considers multiple dimensions: service quality, atmosphere, price level, target clientele
- Matches venues to needs based on semantic understanding

**语义场所分析**
- 分析超越类别分类的场所
- 考虑多个维度：服务质量、氛围、价格水平、目标客群
- 基于语义理解将场所与需求匹配

### Writing Style Analysis
- Analyzes user review patterns for vocabulary, structure, and focus areas
- Can generate content matching individual user styles
- Helps in understanding user preferences and values

**写作风格分析**
- 分析用户评论的词汇、结构和关注领域模式
- 可以生成匹配个人用户风格的内容
- 有助于理解用户偏好和价值观

## 📊 Example Implementation

**User Profile**: Professional seeking efficiency and quality
- **Primary Need**: Professional nail services
- **Secondary Need**: Relaxation services
- **Potential Need**: Skincare consultation

**Generated Recommendations**:
1. Professional nail salon (Primary-1)
2. Spa with relaxation services (Secondary-1)
3. Another professional nail salon (Primary-4)
4. Beauty center with skincare services (Potential/Secondary-2)
5. Full-service nail salon (Primary-5)

**实现示例**

**用户画像**：追求效率和质量的专业人士
- **主要需求**：专业美甲服务
- **次要需求**：放松服务
- **潜在需求**：护肤咨询

**生成的推荐**：
1. 专业美甲沙龙（主要-1）
2. 提供放松服务的水疗中心（次要-1）
3. 另一家专业美甲沙龙（主要-4）
4. 提供护肤服务的美容中心（潜在/次要-2）
5. 全方位服务美甲沙龙（主要-5）

## 📈 Expected Outcomes

### User Experience Goals
- Satisfy immediate needs with first recommendation
- Introduce variety without overwhelming choice
- Enable discovery of relevant new options
- Reduce decision fatigue through strategic curation

**用户体验目标**
- 通过第一个推荐满足即时需求
- 在不压倒选择的情况下引入多样性
- 促进发现相关新选项
- 通过策略性筛选减少决策疲劳

### System Performance Metrics
- User engagement with diverse recommendation types
- Discovery rate of new venues
- Satisfaction across different need categories
- Reduction in choice abandonment

**系统性能指标**
- 用户对不同推荐类型的参与度
- 新场所发现率
- 不同需求类别的满意度
- 选择放弃的减少

## 🔬 Technical Contributions

The system introduces several approaches to recommendation systems:

1. **Multi-tier Need Classification**: Systematic categorization of user needs into primary, secondary, and potential types
2. **Strategic Ordering**: Recommendation sequencing based on cognitive considerations rather than simple ranking
3. **Semantic Matching**: Venue-need matching using semantic analysis rather than category-based filtering
4. **Third-party Perspective Integration**: Using mentions of users in reviews as additional data sources

**技术贡献**

系统为推荐系统引入了几种方法：

1. **多层需求分类**：将用户需求系统性分类为主要、次要和潜在类型
2. **策略性排序**：基于认知考虑而非简单排名的推荐排序
3. **语义匹配**：使用语义分析而非基于类别过滤的场所-需求匹配
4. **第三方视角整合**：使用评论中对用户的提及作为额外数据源

## 🚀 Application Domains

The approach can be applied to various recommendation contexts:
- Restaurant and dining recommendations
- Beauty and wellness services
- Retail and shopping venues
- Entertainment and leisure activities
- Travel and accommodation planning

**应用领域**

该方法可应用于各种推荐场景：
- 餐厅和用餐推荐
- 美容和保健服务
- 零售和购物场所
- 娱乐和休闲活动
- 旅行和住宿规划

## 🔧 Implementation Considerations

### Data Requirements
- User review history with sufficient volume
- Venue information beyond basic categories
- Review content for semantic analysis
- Optional: User mention data in reviews

**数据要求**
- 具有足够数量的用户评论历史
- 超越基本类别的场所信息
- 用于语义分析的评论内容
- 可选：评论中的用户提及数据

### Technical Dependencies
- Natural language processing capabilities
- Semantic analysis tools
- User profiling algorithms
- Recommendation ranking systems

**技术依赖**
- 自然语言处理能力
- 语义分析工具
- 用户画像算法
- 推荐排名系统

---

**MyGO**: A structured approach to multi-dimensional user need satisfaction in recommendation systems.

**MyGO**：推荐系统中多维用户需求满足的结构化方法。
