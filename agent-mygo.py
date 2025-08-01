from agentsociety.agent import IndividualAgentBase 
from typing import Any, List, Dict
import json
import math
import re

class SimplifiedRecommendationAgent(IndividualAgentBase):
    """精简版推荐智能体 - 单LLM初筛 + 最终选择 + 用户名提及分析"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.print_prompts = kwargs.get('print_prompts', True)
        self.debug_communication = kwargs.get('debug_communication', True)
    
    def safe_print(self, text):
        try: print(text)
        except: print(str(text).encode('ascii', 'ignore').decode('ascii'))

    def _print_prompt(self, messages: List[Dict], task_type: str, llm_role: str = ""):
        if not self.print_prompts: return
        separator = "=" * 80
        self.safe_print(f"\n{separator}\nPROMPT - {task_type} [{llm_role}]\n{separator}")
        for message in messages:
            self.safe_print(f"\n[{message.get('role', 'unknown').upper()}]:\n{'-'*60}\n{message.get('content', '')}\n{'-'*60}")
        self.safe_print(f"{separator}\n")

    def _parse_json(self, response: str) -> Dict:
        try:
            json_text = response.split("```json")[1].split("```")[0].strip() if "```json" in response else response
            json_text = re.sub(r'//.*', '', json_text)
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            return json.loads(json_text.strip())
        except: return {}

    def _extract_main_category(self, categories_str: str) -> str:
        return (categories_str.split(',')[0].strip() if categories_str and categories_str != 'Unknown' else 'Unknown')

    def _tokenize_text(self, text: str) -> List[str]:
        """简单分词：使用正则表达式分割单词"""
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        return words

    def _analyze_user_preferences(self, user_reviews: List[Dict], tool) -> Dict[str, Any]:
        if not user_reviews: return {}
        
        ratings = [r['stars'] for r in user_reviews]
        preferences = {
            "avg_rating": round(sum(ratings) / len(ratings), 1),
            "review_count": len(user_reviews),
            "category_preferences": {},
        }

        venue_ratings = []
        
        for review in user_reviews:
            item_info = tool.get_item(review.get('item_id'))
            if not item_info: continue
            
            venue_avg_rating = item_info.get('stars', 0)
            if venue_avg_rating > 0:
                venue_ratings.append(venue_avg_rating)
            
            category = self._extract_main_category(item_info.get('categories', 'Unknown'))
            if category not in preferences["category_preferences"]:
                preferences["category_preferences"][category] = {'count': 0, 'ratings': []}
            preferences["category_preferences"][category]['count'] += 1
            preferences["category_preferences"][category]['ratings'].append(review['stars'])
        
        if venue_ratings:
            preferences["visited_venues_avg_rating"] = round(sum(venue_ratings) / len(venue_ratings), 2)
        else:
            preferences["visited_venues_avg_rating"] = 0.0
        
        for data in preferences["category_preferences"].values():
            data['avg_rating'] = round(sum(data['ratings']) / len(data['ratings']), 1)
        
        return preferences

    def _build_candidate_details(self, candidate_list: List[str], tool) -> List[Dict]:
        candidate_details = []
        filtered_count = 0
        
        for item_id in candidate_list:
            item_info = tool.get_item(item_id)
            if not item_info: continue
            
            item_reviews = tool.get_reviews(item_id=item_id)
            avg_rating = item_info.get('stars', 0) or (sum(r['stars'] for r in item_reviews) / len(item_reviews) if item_reviews else 0)
            
            # 预筛选：排除平均评分小于等于1.5的地点
            if avg_rating <= 1.5:
                filtered_count += 1
                continue
            
            candidate_details.append({
                "item_id": item_id,
                "name": item_info.get('name', 'Unknown'),
                "category": self._extract_main_category(item_info.get('categories', 'Unknown')),
                "avg_rating": round(avg_rating, 1),
                "review_count": len(item_reviews) if item_reviews else 0,
                "city": item_info.get('city', 'Unknown'),
                "reviews": item_reviews[:5] if item_reviews else []
            })
        
        if self.print_prompts and filtered_count > 0:
            self.safe_print(f"🔍 预筛选: 过滤掉{filtered_count}个低评分地点(评分<=1.5)")
            
        return candidate_details

    def _get_user_relevant_reviews(self, user_reviews: List[Dict], candidate_categories: List[str], tool, limit: int = 6) -> str:
        if not user_reviews or not candidate_categories: return "用户在相关类别下无历史评论"
        
        relevant_reviews = []
        for review in user_reviews:
            item_info = tool.get_item(review.get('item_id'))
            if not item_info: continue
            
            item_category = self._extract_main_category(item_info.get('categories', 'Unknown'))
            if item_category in candidate_categories:
                relevant_reviews.append({
                    'rating': review['stars'], 'text': review['text'],
                    'category': item_category, 'venue_name': item_info.get('name', 'Unknown'),
                    'useful': review.get('useful', 0),
                    'date': review.get('date', '')
                })
        
        if not relevant_reviews: return "用户在相关类别下无历史评论"
        
        try:
            selected_reviews = sorted(relevant_reviews, key=lambda x: x.get('date', ''), reverse=True)[:limit]
        except:
            selected_reviews = sorted(relevant_reviews, key=lambda x: x['useful'], reverse=True)[:limit]   
        
        examples = ["用户在相关类别下的历史评论示例："]
        for i, review in enumerate(selected_reviews, 1):
            text = review['text'][:120] + "..." if len(review['text']) > 120 else review['text']
            useful_info = f" ({review['useful']}个有用)" if review['useful'] > 0 else ""
            date_info = f" {review.get('date', '')[:10]}" if review.get('date') else ""
            examples.append(f"\n{i}. [{review['rating']}星{useful_info}]{date_info} {review['venue_name']} ({review['category']})")
            examples.append(f"   \"{text}\"")
        
        return "\n".join(examples)

    def _format_venues_for_screening(self, candidate_details: List[Dict]) -> str:
        formatted_venues = []
        
        for i, venue in enumerate(candidate_details, 1):
            venue_info = f"""{i}. {venue['name']} (ID: {venue['item_id']})
   类别: {venue['category']} | 评分: {venue['avg_rating']}⭐ ({venue['review_count']}条评论)"""
            
            reviews = venue.get('reviews', [])
            if reviews:
                venue_info += "\n   代表性评论:"
                for j, review in enumerate(reviews[:3], 1):
                    review_text = review.get('text', '')[:120] + "..." if len(review.get('text', '')) > 120 else review.get('text', '')
                    useful_info = f" ({review.get('useful', 0)}个有用)" if review.get('useful', 0) > 0 else ""
                    venue_info += f"\n     {j}. [{review.get('stars', 0)}⭐{useful_info}] \"{review_text}\""
            else:
                venue_info += "\n   代表性评论: 暂无评论"
            
            formatted_venues.append(venue_info)
        
        return "\n\n".join(formatted_venues)

    def _check_user_mentioned_in_reviews(self, user_name: str, candidate_list: List[str], tool) -> Dict[str, Any]:
        """检查用户名在评论中的提及情况，返回详细信息"""
        if not user_name or len(user_name.strip()) < 2:
            return {"mentioned_venues": [], "venue_count": 0, "mention_details": []}
        
        user_name_clean = user_name.strip().lower()
        mentioned_venues = []
        mention_details = []
        
        for item_id in candidate_list:
            item_reviews = tool.get_reviews(item_id=item_id)
            
            if not item_reviews:
                continue
            
            # 获取场所信息
            item_info = tool.get_item(item_id)
            venue_name = item_info.get('name', 'Unknown') if item_info else 'Unknown'
            
            venue_mentions = []
            for review in item_reviews:
                review_text = review.get('text', '')
                
                # 分词后检查是否包含用户名
                words = self._tokenize_text(review_text)
                if user_name_clean in words:
                    venue_mentions.append(review_text)
            
            if venue_mentions:
                mentioned_venues.append(item_id)
                mention_details.append({
                    "venue_id": item_id,
                    "venue_name": venue_name,
                    "mentions": venue_mentions
                })
        
        if self.print_prompts:
            venue_count = len(mentioned_venues)
            if venue_count > 0:
                self.safe_print(f"✅ 发现用户名: '{user_name_clean}' (在{venue_count}个场所)")
                for detail in mention_details:
                    self.safe_print(f"📍 {detail['venue_name']}: {len(detail['mentions'])}条提及")
            else:
                self.safe_print(f"❌ 未发现用户名: '{user_name_clean}'")
        
        return {
            "mentioned_venues": mentioned_venues,
            "venue_count": len(mentioned_venues),
            "mention_details": mention_details
        }

    def _build_user_mention_context(self, mention_details: List[Dict]) -> str:
        """构建用户名提及的上下文信息"""
        if not mention_details:
            return ""
        
        context_parts = ["检测到以下场所的评论中提及了用户名，这些可能是其他用户对目标用户评论的回复："]
        
        for detail in mention_details:
            venue_name = detail["venue_name"]
            mentions = detail["mentions"]
            
            context_parts.append(f"\n【{venue_name}】包含用户名的评论:")
            for i, mention in enumerate(mentions, 1):
                # 不截断，显示完整评论
                context_parts.append(f"{i}. \"{mention}\"")
        
        context_parts.append(f"""
注意：请仔细分析这些评论内容：
1. 判断这些提及是否真的是对用户评论的回复，还可能是：
   - 提及同名的服务人员、其他顾客
   - 无关的人名巧合
   - 其他上下文中的用户名使用
2. 如果确实是对用户评论的回复，可以从中推断：
   - 用户对该场所的真实态度和体验
   - 用户的具体需求和偏好
   - 用户在该场所的行为模式
3. 将这些信息作为用户偏好分析的重要补充""")
        
        return "\n".join(context_parts)

    async def _intent_analysis_llm(self, user_preferences: Dict, candidate_details: List[Dict], candidate_category: str, user_reviews: List[Dict], tool, user_id: str, mention_info: Dict[str, Any]) -> Dict[str, Any]:
        """意图分析LLM - 分析用户画像和多层次需求"""
        
        # 获取用户信息
        user_info = tool.get_user(user_id)
        user_name = user_info.get('name', user_id) if user_info else user_id
        
        # 构建候选类别分析
        candidate_categories = list(set(c.get('category', 'Unknown') for c in candidate_details if c.get('category') != 'Unknown'))
        category_analysis = self._build_category_analysis_text(user_preferences, candidate_categories)
        
        # 获取用户相关评论，不限制数量以获得更全面的分析
        user_relevant_reviews = self._get_user_relevant_reviews(user_reviews, candidate_categories, tool, limit=len(user_reviews))
        
        # 构建用户名提及上下文
        mention_context = ""
        if mention_info["venue_count"] > 0 and mention_info["venue_count"] < 4:
            mention_context = self._build_user_mention_context(mention_info["mention_details"])

        user_prompt = f"""
用户基本信息: 
- 用户名: {user_name}
- 平均评分: {user_preferences.get('avg_rating', 3)}星
- 评论总数: {user_preferences.get('review_count', 0)}条
- 访问地点的平均评分: {user_preferences.get('visited_venues_avg_rating', 0)}星

{category_analysis}

{user_relevant_reviews}

{mention_context}

请基于用户的历史行为模式，分析用户的基本画像和多层次需求。

输出格式：
```json
{{
    "user_profile": "用户xxx是一名……的用户，偏好……特质",
    "primary_need": "具体的主要需求，如'美甲服务'",
    "secondary_need": "具体的次要需求，如'美发服务'", 
    "potential_need": "具体的潜在需求，如'美容护理'"
}}
```"""

        messages = [
            {"role": "system", "content": "你是资深的用户行为分析专家。请严格按照要求格式输出：1)用户画像（一句话描述用户特征和偏好特质）2)主要需求（最核心的具体需求）3)次要需求（重要但非核心的具体需求）4)潜在需求（可能感兴趣但未明确表达的具体需求）。每项都要具体明确，不要添加其他内容。"},
            {"role": "user", "content": user_prompt}
        ]
        self._print_prompt(messages, "INTENT_ANALYSIS", "Intent Analyzer")
        
        response = await self.llm.atext_request(messages)
        return self._parse_json(response)

    def _build_category_analysis_text(self, user_preferences: Dict, candidate_categories: List[str]) -> str:
        """构建类别分析文本"""
        category_prefs = user_preferences.get('category_preferences', {})
        if not category_prefs: return "用户无历史评分记录"
        
        analysis_parts = ["用户在候选相关类别下的历史访问记录："]
        relevant_categories = [(cat, data) for cat, data in category_prefs.items() if cat in candidate_categories]
        relevant_categories.sort(key=lambda x: x[1]['count'], reverse=True)
        
        if relevant_categories:
            for category, data in relevant_categories:
                analysis_parts.append(f"- {category}: {data['count']}次访问 (平均{data['avg_rating']}星)")
        else:
            analysis_parts.append("- 用户在候选类别下无历史访问记录")
        
        total_visits = sum(data['count'] for data in category_prefs.values())
        relevant_visits = sum(data['count'] for _, data in relevant_categories)
        if total_visits > 0:
            analysis_parts.append(f"\n候选相关类别访问占比: {relevant_visits}/{total_visits} ({relevant_visits/total_visits:.1%})")
        
        return "\n".join(analysis_parts)
    
    async def _handle_recommendation(self, task_context: Dict) -> Dict[str, Any]:
        user_id, candidate_list, candidate_category = task_context["user_id"], task_context["candidate_list"], task_context["candidate_category"]
        tool = self.toolbox.get_tool_object("uir")
        
        if self.print_prompts: self.safe_print(f"\n🎭 分层需求推荐: 用户{user_id}, 候选{len(candidate_list)}个")
        
        try:
            user_reviews = tool.get_reviews(user_id=user_id)
            user_preferences = self._analyze_user_preferences(user_reviews, tool)
            candidate_details = self._build_candidate_details(candidate_list, tool)
            
            # 检查用户名在评论中的提及情况
            user_info = tool.get_user(user_id)
            user_name = user_info.get('name', '') if user_info else ''
            
            mention_info = {"mentioned_venues": [], "venue_count": 0, "mention_details": []}
            if user_name:
                mention_info = self._check_user_mentioned_in_reviews(user_name, candidate_list, tool)

            # 检查预筛选后是否还有足够的候选
            if len(candidate_details) < 5:
                if self.print_prompts: 
                    self.safe_print(f"⚠️ 预筛选后候选数量不足: {len(candidate_details)}个，直接返回剩余候选")
                return {"item_list": [c['item_id'] for c in candidate_details]}
            
            if self.print_prompts: 
                self.safe_print(f"✅ 预筛选后保留{len(candidate_details)}个优质候选，开始分层推荐")
            
            # 第一阶段：意图分析LLM - 识别用户画像和分层需求
            if self.print_prompts: self.safe_print(f"\n🧠 第一阶段: 意图分析LLM")
            intent_result = await self._intent_analysis_llm(user_preferences, candidate_details, candidate_category, user_reviews, tool, user_id, mention_info)
            
            user_profile = intent_result.get('user_profile', '用户画像分析不可用')
            primary_need = intent_result.get('primary_need', '主要需求未识别')
            secondary_need = intent_result.get('secondary_need', '次要需求未识别')
            potential_need = intent_result.get('potential_need', '潜在需求未识别')
            
            if self.print_prompts:
                self.safe_print(f"   用户画像: {user_profile}")
                self.safe_print(f"   主要需求: {primary_need}")
                self.safe_print(f"   次要需求: {secondary_need}")
                self.safe_print(f"   潜在需求: {potential_need}")
            
            # 根据需求层次对场所进行分类
            categorized_venues = self._categorize_venues_by_needs(candidate_details, primary_need, secondary_need, potential_need)
            
            if self.print_prompts:
                self.safe_print(f"   场所分类: 主要需求{len(categorized_venues['primary'])}个, 次要需求{len(categorized_venues['secondary'])}个, 潜在需求{len(categorized_venues['potential'])}个, 其他{len(categorized_venues['other'])}个")
            
            # 检查主要需求场所是否足够
            primary_venues = categorized_venues['primary']
            if len(primary_venues) < 3:
                # 如果主要需求场所不足，从其他类别补充
                primary_venues.extend(categorized_venues['other'][:5-len(primary_venues)])
                if self.print_prompts:
                    self.safe_print(f"   主要需求场所不足，从其他类别补充到{len(primary_venues)}个")
            
            # 第二阶段：主要需求初筛LLM (选出10个)
            if self.print_prompts: self.safe_print(f"\n🎯 第二阶段: 主要需求初筛LLM ({len(primary_venues)}个→10个)")
            
            primary_screening_result = await self._primary_need_screening_llm(user_preferences, primary_venues, user_profile, primary_need, user_reviews, tool, user_id)
            selected_primary_venues = primary_screening_result.get('selected_venues', [])
            
            if self.print_prompts: self.safe_print(f"   主要需求初筛完成，选出{len(selected_primary_venues)}个候选")
            
            # 第三阶段：主要需求最终选择LLM (选出5个)
            if self.print_prompts: self.safe_print(f"\n👑 第三阶段: 主要需求最终选择LLM (10个→5个)")
            
            final_primary_result = await self._final_selection_llm(user_preferences, selected_primary_venues, primary_venues, user_profile, primary_need)
            final_primary_recommendations = final_primary_result.get('final_recommendations', [])
            
            if self.print_prompts: self.safe_print(f"   主要需求最终选择完成，选出{len(final_primary_recommendations)}个推荐")
            
            # 第四阶段：次要和潜在需求推荐LLM (选出3个)
            secondary_potential_recommendations = []
            secondary_venues = categorized_venues['secondary']
            potential_venues = categorized_venues['potential']
            
            if secondary_venues or potential_venues:
                if self.print_prompts: self.safe_print(f"\n🔍 第四阶段: 次要和潜在需求推荐LLM ({len(secondary_venues)}+{len(potential_venues)}个→3个)")
                
                secondary_potential_result = await self._secondary_potential_needs_llm(
                    user_preferences, secondary_venues, potential_venues, 
                    user_profile, secondary_need, potential_need, 
                    user_reviews, tool, user_id
                )
                secondary_potential_venues = secondary_potential_result.get('recommended_venues', [])
                secondary_potential_recommendations = [v['venue_id'] for v in secondary_potential_venues]
                
                if self.print_prompts: 
                    self.safe_print(f"   次要和潜在需求推荐完成，选出{len(secondary_potential_recommendations)}个推荐")
                    for venue in secondary_potential_venues:
                        self.safe_print(f"     - {venue['venue_name']} ({venue['need_type']}): {venue['selection_reason']}")
            else:
                if self.print_prompts: self.safe_print(f"\n🔍 第四阶段: 无次要和潜在需求场所，跳过")
            
            # 合并最终推荐结果 (5个主要需求 + 3个次要/潜在需求 = 8个总推荐)
            all_recommendations = final_primary_recommendations + secondary_potential_recommendations
            
            # 确保不超过推荐数量限制，优先保证主要需求
            if len(all_recommendations) > 8:
                all_recommendations = final_primary_recommendations[:5] + secondary_potential_recommendations[:3]
            
            # 如果总推荐不足，从剩余候选中补充
            if len(all_recommendations) < 5:
                remaining_candidates = [c['item_id'] for c in candidate_details if c['item_id'] not in all_recommendations]
                all_recommendations.extend(remaining_candidates[:5-len(all_recommendations)])
            
            if self.print_prompts:
                self.safe_print(f"\n🎉 分层需求推荐完成! 总推荐{len(all_recommendations)}个")
                self.safe_print(f"📊 流程: {len(candidate_list)}个候选 → 意图分析 → 主要需求({len(final_primary_recommendations)}) + 次要/潜在需求({len(secondary_potential_recommendations)}) → {len(all_recommendations)}个最终推荐")
                self.safe_print(f"🏆 最终推荐列表: {all_recommendations}")
            
            return {"item_list": all_recommendations}
        
        except Exception as e:
            if self.print_prompts: self.safe_print(f"❌ 分层需求推荐出错: {e}")
            return {"item_list": candidate_list[:5]}

    def _analyze_user_review_style(self, user_reviews: List[Dict], tool) -> Dict[str, Any]:
        if not user_reviews:
            return {"avg_rating": 3.0, "review_count": 0, "avg_text_length": 50, "category_preferences": {}}
        
        ratings = [r['stars'] for r in user_reviews]
        text_lengths = [len(r['text']) for r in user_reviews]
        
        basic_stats = {
            "avg_rating": round(sum(ratings) / len(ratings), 1),
            "review_count": len(user_reviews),
            "avg_text_length": round(sum(text_lengths) / len(text_lengths)),
            "positive_ratio": round(sum(1 for r in ratings if r >= 4) / len(ratings), 2),
        }
        
        category_preferences = {}
        
        for review in user_reviews:
            item_info = tool.get_item(review.get('item_id'))
            if not item_info: continue
            
            category = self._extract_main_category(item_info.get('categories', 'Unknown'))
            if category not in category_preferences:
                category_preferences[category] = {'count': 0, 'ratings': []}
            category_preferences[category]['count'] += 1
            category_preferences[category]['ratings'].append(review['stars'])
        
        for data in category_preferences.values():
            data['avg_rating'] = round(sum(data['ratings']) / len(data['ratings']), 1)
        
        return {**basic_stats, 'category_preferences': category_preferences}

    def _parse_review_response(self, response: str, user_preferences: Dict) -> Dict[str, Any]:
        try:
            result = self._parse_json(response)
            if result.get("stars") and result.get("review"):
                stars = result["stars"]
                if isinstance(stars, int) and 1 <= stars <= 5:
                    review_text = result["review"].strip()
                    max_length = 120
                    if len(review_text) > max_length: review_text = review_text[:max_length-3] + "..."
                    return {"stars": stars, "review": review_text}
        
        except Exception as e:
            if self.print_prompts: self.safe_print(f"评论解析错误: {e}")
        
        default_rating = max(1, min(5, round(user_preferences.get("avg_rating", 3))))
        sentences = [s.strip() for s in response.replace('\n', '. ').split('.') if len(s.strip()) > 20]
        default_review = sentences[0] if sentences else "This place has good quality."
        
        max_length = 120
        if len(default_review) > max_length: default_review = default_review[:max_length-3] + "..."
        
        return {"stars": default_rating, "review": default_review}

    async def _generate_review(self, user_id: str, item_id: str, tool) -> Dict[str, Any]:
        user_reviews = tool.get_reviews(user_id=user_id)
        item_info = tool.get_item(item_id)
        item_reviews = tool.get_reviews(item_id=item_id)
        
        if not item_info: return {"stars": 3, "review": "This place seems decent."}
        
        user_preferences = self._analyze_user_review_style(user_reviews, tool)
        target_category = self._extract_main_category(item_info.get('categories', 'Unknown'))
        item_avg_rating = item_info.get('stars', 0) or (sum(r['stars'] for r in item_reviews) / len(item_reviews) if item_reviews else 3)
        
        # 构建用户偏好摘要
        category_prefs = user_preferences.get('category_preferences', {})
        preference_parts = [
            f"用户评价习惯: 平均{user_preferences.get('avg_rating', 3)}星，共{user_preferences.get('review_count', 0)}条评价",
            f"积极评价比例: {user_preferences.get('positive_ratio', 0)*100:.0f}%"
        ]
        
        if target_category in category_prefs:
            target_stats = category_prefs[target_category]
            preference_parts.append(f"在{target_category}类别: 评价{target_stats['count']}次，平均{target_stats['avg_rating']}星")
        
        preference_summary = "\n".join(preference_parts)
        
        # 获取用户相关评论示例
        candidate_categories = [target_category]
        user_relevant_reviews = self._get_user_relevant_reviews(user_reviews, candidate_categories, tool, limit=5)

        system_prompt = """你是一个评价写手，需要根据用户的历史行为模式为场所写出符合该用户风格的评价。

要求：
1. 评分要符合用户的评分习惯和对该类场所的偏好
2. 评价文本要模仿用户的写作风格，长度控制在30-50词
3. 内容要合理，关注用户历史上重视的场所特征"""

        user_prompt = f"""用户偏好分析：
{preference_summary}

{user_relevant_reviews}

目标场所信息：
- 场所名称: {item_info.get('name', 'Unknown')}
- 场所类别: {target_category}
- 该场所平均评分: {item_avg_rating:.1f}星

请根据用户的偏好模式生成一条评价。

输出格式：
```json
{{
    "stars": [1-5的整数评分],
    "review": "[模仿用户风格的评价文本，30-50词]"
}}
```"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self._print_prompt(messages, "REVIEW_GENERATION", "Review Generator")
        response = await self.llm.atext_request(messages)
        return self._parse_review_response(response, user_preferences)

    async def forward(self, task_context: dict[str, Any]):
        target = task_context["target"]
        if target == "recommendation":
            return await self._handle_recommendation(task_context)
        elif target == "review_writing":
            user_id, item_id = task_context["user_id"], task_context["item_id"]
            tool = self.toolbox.get_tool_object("uir")
            return await self._generate_review(user_id, item_id, tool)
        else:
            raise ValueError(f"Unknown target: {target}")

    async def _primary_need_screening_llm(self, user_preferences: Dict, candidate_details: List[Dict], user_profile: str, primary_need: str, secondary_need: str, potential_need: str, user_reviews: List[Dict], tool, user_id: str) -> Dict[str, Any]:
        """主要需求初筛LLM - 从所有候选中识别主要需求相关场所并选出10个"""
        
        # 获取用户信息
        user_info = tool.get_user(user_id)
        user_name = user_info.get('name', user_id) if user_info else user_id
        
        # 格式化所有候选场所
        venues_formatted = self._format_venues_for_screening(candidate_details)
        
        # 构建用户相关评论
        candidate_categories = list(set(v.get('category', 'Unknown') for v in candidate_details))
        user_relevant_reviews = self._get_user_relevant_reviews(user_reviews, candidate_categories, tool, limit=6)

        system_prompt = """你是推荐系统的主要需求筛选专家，专门负责识别和推荐满足用户核心需求的场所。

你的任务：
基于用户画像和主要需求，从所有候选场所中识别并选出10个最符合用户主要需求的地点。

重要原则：
1. 严格聚焦于用户的主要需求，优先识别和推荐直接满足主要需求的场所
2. 可以考虑能够间接满足主要需求的相关场所
3. 优先考虑场所质量和用户评分习惯的匹配
4. 重视用户历史行为模式和偏好特质
5. 确保推荐的多样性，避免过于单一"""

        user_prompt = f"""用户画像: {user_profile}

主要需求: {primary_need}
次要需求: {secondary_need}
潜在需求: {potential_need}

用户基本信息:
- 用户名: {user_name}
- 平均评分: {user_preferences.get('avg_rating', 3)}星
- 评论总数: {user_preferences.get('review_count', 0)}条
- 访问地点的平均评分: {user_preferences.get('visited_venues_avg_rating', 0)}星

{user_relevant_reviews}

所有候选场所列表:
{venues_formatted}

请从以上所有候选场所中识别并选择10个最能满足用户主要需求"{primary_need}"的场所。
【注意：深度思考后再回答】

输出格式：
```json
{{
    "selected_venues": [
        {{
            "venue_id": "场所ID",
            "venue_name": "场所名称",
            "selection_reason": "选择理由，说明如何满足主要需求"
        }}
    ]
}}
```"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        self._print_prompt(messages, "PRIMARY_NEED_SCREENING", "Primary Need Screening LLM")
        
        response = await self.llm.atext_request(messages)
        result = self._parse_json(response)
        
        # 验证结果
        if 'selected_venues' not in result: result['selected_venues'] = []
        valid_ids = {v['item_id'] for v in candidate_details}
        validated_venues = []
        
        for venue in result['selected_venues'][:10]:
            if isinstance(venue, dict) and venue.get('venue_id') in valid_ids:
                validated_venues.append({
                    'venue_id': venue.get('venue_id'),
                    'venue_name': venue.get('venue_name', 'Unknown'),
                    'selection_reason': venue.get('selection_reason', '满足主要需求')
                })
        
        # 如果不足10个，从剩余候选中补充高评分场所
        if len(validated_venues) < 10:
            selected_ids = {v['venue_id'] for v in validated_venues}
            remaining = [v for v in candidate_details if v['item_id'] not in selected_ids]
            remaining.sort(key=lambda x: x['avg_rating'], reverse=True)
            
            for venue in remaining:
                if len(validated_venues) >= 10: break
                validated_venues.append({
                    'venue_id': venue['item_id'],
                    'venue_name': venue['name'],
                    'selection_reason': f"高质量候选场所 (评分{venue['avg_rating']})"
                })
        
        result['selected_venues'] = validated_venues[:10]
        return result

    async def _final_selection_llm(self, user_preferences: Dict, selected_venues: List[Dict], candidate_details: List[Dict], user_profile: str, primary_need: str) -> Dict[str, Any]:
        """最终选择LLM - 从10个主要需求推荐中选出最终5个"""
        
        # 构建候选详情映射
        venue_details_map = {venue['item_id']: venue for venue in candidate_details}
        
        # 格式化选中的场所信息
        venues_info = []
        for i, venue in enumerate(selected_venues, 1):
            venue_id = venue.get('venue_id')
            venue_name = venue.get('venue_name', 'Unknown')
            selection_reason = venue.get('selection_reason', 'N/A')
            
            venue_detail = venue_details_map.get(venue_id, {})
            
            venue_info = f"""{i}. {venue_name} (ID: {venue_id})
   类别: {venue_detail.get('category', 'Unknown')} | 评分: {venue_detail.get('avg_rating', 0)}⭐ ({venue_detail.get('review_count', 0)}条评论)
   选择理由: {selection_reason}"""
            
            reviews = venue_detail.get('reviews', [])
            if reviews:
                venue_info += "\n   代表性评论:"
                for j, review in enumerate(reviews[:3], 1):
                    review_text = review.get('text', '')[:100] + "..." if len(review.get('text', '')) > 100 else review.get('text', '')
                    useful_info = f" ({review.get('useful', 0)}个有用)" if review.get('useful', 0) > 0 else ""
                    venue_info += f"\n     {j}. [{review.get('stars', 0)}⭐{useful_info}] \"{review_text}\""
            else:
                venue_info += "\n   代表性评论: 暂无评论"
            
            venues_info.append(venue_info)
        
        venues_text = "\n\n".join(venues_info)
        
        system_prompt = """你是推荐系统的最终决策专家，需要从10个主要需求初筛推荐中选出最终的5个推荐。

你的任务：
综合考虑用户画像、主要需求匹配度、场所质量，选出用户最有可能访问的5个地点，并按优先级排序。

决策原则：
1. 严格聚焦主要需求，优先选择最符合核心需求的场所
2. 第一个推荐尤其重要，应该是最符合用户画像和主要需求的
3. 考虑场所质量和用户评分习惯的匹配
4. 适度考虑多样性，但不偏离主要需求
5. 重点参考用户评论了解场所的真实体验"""

        user_prompt = f"""用户画像: {user_profile}

主要需求: {primary_need}

用户档案:
- 历史平均评分: {user_preferences.get('avg_rating', 3)}星
- 评论数量: {user_preferences.get('review_count', 0)}
- 访问地点的平均评分: {user_preferences.get('visited_venues_avg_rating', 0)}星

初筛选出的10个主要需求场所:
{venues_text}

请从以上10个场所中选择5个最终推荐，按优先级从高到低排序。

【注意：深度思考后再回答】

输出格式：
```json
{{
    "final_recommendations": ["场所ID1", "场所ID2", "场所ID3", "场所ID4", "场所ID5"],
    "selection_rationale": "详细选择理由，说明为什么选择这5个场所以及优先级排序的逻辑"
}}
```"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        self._print_prompt(messages, "FINAL_SELECTION", "Final Selection LLM")
        
        response = await self.llm.atext_request(messages)
        result = self._parse_json(response)
        
        if 'final_recommendations' not in result: result['final_recommendations'] = []
        valid_ids = {venue['venue_id'] for venue in selected_venues}
        validated_recommendations = [vid for vid in result['final_recommendations'] if vid in valid_ids]
        
        # 如果不足5个，从初筛结果中补充
        if len(validated_recommendations) < 5:
            for venue in selected_venues:
                if venue['venue_id'] not in validated_recommendations and len(validated_recommendations) < 5:
                    validated_recommendations.append(venue['venue_id'])
        
        result['final_recommendations'] = validated_recommendations[:5]
        return result

    async def _secondary_potential_needs_llm(self, user_preferences: Dict, candidate_details: List[Dict], user_profile: str, secondary_need: str, potential_need: str, primary_recommendations: List[str], user_reviews: List[Dict], tool, user_id: str) -> Dict[str, Any]:
        """次要和潜在需求推荐LLM - 从所有候选中识别次要和潜在需求相关场所"""
        
        # 获取用户信息
        user_info = tool.get_user(user_id)
        user_name = user_info.get('name', user_id) if user_info else user_id
        
        # 排除已经推荐的主要需求场所
        remaining_venues = [v for v in candidate_details if v['item_id'] not in primary_recommendations]
        venues_formatted = self._format_venues_for_screening(remaining_venues)

        system_prompt = """你是推荐系统的次要需求专家，负责识别和推荐满足用户次要需求和潜在需求的场所。

你的任务：
基于用户画像、次要需求和潜在需求，从剩余候选场所中识别并选出3个推荐（优先次要需求，适当考虑潜在需求）。

推荐原则：
1. 优先识别和推荐能满足次要需求的场所
2. 适当考虑能满足潜在需求的场所，发掘用户可能感兴趣的新体验
3. 结合用户画像和偏好特质
4. 确保推荐的场所质量符合用户标准
5. 提供与主要需求不同的多样化体验"""

        user_prompt = f"""用户画像: {user_profile}

次要需求: {secondary_need}
潜在需求: {potential_need}

用户基本信息:
- 用户名: {user_name}
- 平均评分: {user_preferences.get('avg_rating', 3)}星
- 评论总数: {user_preferences.get('review_count', 0)}条
- 访问地点的平均评分: {user_preferences.get('visited_venues_avg_rating', 0)}星

剩余候选场所（已排除主要需求推荐）:
{venues_formatted}

请从以上场所中识别并选择3个能满足次要需求或潜在需求的场所推荐。
【注意：深度思考后再回答】

输出格式：
```json
{{
    "recommended_venues": [
        {{
            "venue_id": "场所ID",
            "venue_name": "场所名称",
            "need_type": "secondary或potential",
            "selection_reason": "选择理由，说明满足哪种需求"
        }}
    ]
}}
```"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        self._print_prompt(messages, "SECONDARY_POTENTIAL_NEEDS", "Secondary & Potential Needs LLM")
        
        response = await self.llm.atext_request(messages)
        result = self._parse_json(response)
        
        # 验证结果
        if 'recommended_venues' not in result: result['recommended_venues'] = []
        valid_ids = {v['item_id'] for v in remaining_venues}
        validated_venues = []
        
        for venue in result['recommended_venues'][:3]:
            if isinstance(venue, dict) and venue.get('venue_id') in valid_ids:
                validated_venues.append({
                    'venue_id': venue.get('venue_id'),
                    'venue_name': venue.get('venue_name', 'Unknown'),
                    'need_type': venue.get('need_type', 'secondary'),
                    'selection_reason': venue.get('selection_reason', '满足次要/潜在需求')
                })
        
        # 如果不足3个，从剩余高评分场所中补充
        if len(validated_venues) < 3:
            selected_ids = {v['venue_id'] for v in validated_venues}
            remaining_unselected = [v for v in remaining_venues if v['item_id'] not in selected_ids]
            remaining_unselected.sort(key=lambda x: x['avg_rating'], reverse=True)
            
            for venue in remaining_unselected:
                if len(validated_venues) >= 3: break
                validated_venues.append({
                    'venue_id': venue['item_id'],
                    'venue_name': venue['name'],
                    'need_type': 'secondary',
                    'selection_reason': f"高质量补充推荐 (评分{venue['avg_rating']})"
                })
        
        result['recommended_venues'] = validated_venues[:3]
        return result


    async def _handle_recommendation(self, task_context: Dict) -> Dict[str, Any]:
        user_id, candidate_list, candidate_category = task_context["user_id"], task_context["candidate_list"], task_context["candidate_category"]
        tool = self.toolbox.get_tool_object("uir")
        
        if self.print_prompts: self.safe_print(f"\n🎭 分层需求推荐: 用户{user_id}, 候选{len(candidate_list)}个")
        
        try:
            user_reviews = tool.get_reviews(user_id=user_id)
            user_preferences = self._analyze_user_preferences(user_reviews, tool)
            candidate_details = self._build_candidate_details(candidate_list, tool)
            
            # 检查用户名在评论中的提及情况
            user_info = tool.get_user(user_id)
            user_name = user_info.get('name', '') if user_info else ''
            
            mention_info = {"mentioned_venues": [], "venue_count": 0, "mention_details": []}
            if user_name:
                mention_info = self._check_user_mentioned_in_reviews(user_name, candidate_list, tool)

            # 检查预筛选后是否还有足够的候选
            if len(candidate_details) < 5:
                if self.print_prompts: 
                    self.safe_print(f"⚠️ 预筛选后候选数量不足: {len(candidate_details)}个，直接返回剩余候选")
                return {"item_list": [c['item_id'] for c in candidate_details]}
            
            if self.print_prompts: 
                self.safe_print(f"✅ 预筛选后保留{len(candidate_details)}个优质候选，开始分层推荐")
            
            # 第一阶段：意图分析LLM - 识别用户画像和分层需求
            if self.print_prompts: self.safe_print(f"\n🧠 第一阶段: 意图分析LLM")
            intent_result = await self._intent_analysis_llm(user_preferences, candidate_details, candidate_category, user_reviews, tool, user_id, mention_info)
            
            user_profile = intent_result.get('user_profile', '用户画像分析不可用')
            primary_need = intent_result.get('primary_need', '主要需求未识别')
            secondary_need = intent_result.get('secondary_need', '次要需求未识别')
            potential_need = intent_result.get('potential_need', '潜在需求未识别')
            
            if self.print_prompts:
                self.safe_print(f"   用户画像: {user_profile}")
                self.safe_print(f"   主要需求: {primary_need}")
                self.safe_print(f"   次要需求: {secondary_need}")
                self.safe_print(f"   潜在需求: {potential_need}")
            
            # 第二阶段：主要需求初筛LLM (从所有候选中识别并选出10个)
            if self.print_prompts: self.safe_print(f"\n🎯 第二阶段: 主要需求初筛LLM ({len(candidate_details)}个候选→识别并选出10个)")
            
            primary_screening_result = await self._primary_need_screening_llm(
                user_preferences, candidate_details, user_profile, 
                primary_need, secondary_need, potential_need, 
                user_reviews, tool, user_id
            )
            selected_primary_venues = primary_screening_result.get('selected_venues', [])
            
            if self.print_prompts: 
                self.safe_print(f"   主要需求初筛完成，识别并选出{len(selected_primary_venues)}个候选")
                for venue in selected_primary_venues:
                    self.safe_print(f"     - {venue['venue_name']}: {venue['selection_reason']}")
            
            # 第三阶段：主要需求最终选择LLM (选出5个)
            if self.print_prompts: self.safe_print(f"\n👑 第三阶段: 主要需求最终选择LLM (10个→5个)")
            
            final_primary_result = await self._final_selection_llm(
                user_preferences, selected_primary_venues, candidate_details, 
                user_profile, primary_need
            )
            final_primary_recommendations = final_primary_result.get('final_recommendations', [])
            
            if self.print_prompts: self.safe_print(f"   主要需求最终选择完成，选出{len(final_primary_recommendations)}个推荐")
            
            # 第四阶段：次要和潜在需求推荐LLM (从剩余候选中识别并选出3个)
            secondary_potential_recommendations = []
            
            if self.print_prompts: self.safe_print(f"\n🔍 第四阶段: 次要和潜在需求推荐LLM (从剩余候选→识别并选出3个)")
            
            secondary_potential_result = await self._secondary_potential_needs_llm(
                user_preferences, candidate_details, user_profile, 
                secondary_need, potential_need, final_primary_recommendations,
                user_reviews, tool, user_id
            )
            secondary_potential_venues = secondary_potential_result.get('recommended_venues', [])
            secondary_potential_recommendations = [v['venue_id'] for v in secondary_potential_venues]
            
            if self.print_prompts: 
                self.safe_print(f"   次要和潜在需求推荐完成，识别并选出{len(secondary_potential_recommendations)}个推荐")
                for venue in secondary_potential_venues:
                    self.safe_print(f"     - {venue['venue_name']} ({venue['need_type']}): {venue['selection_reason']}")
            
            # Tricky方式合并：主要1+次要1+主要4+次要2+主要5（跳过主要2,3）
            tricky_recommendations = []

            # 添加主要推荐1
            if len(final_primary_recommendations) >= 1:
                tricky_recommendations.append(final_primary_recommendations[0])

            # 添加次要推荐1
            if len(secondary_potential_recommendations) >= 1:
                tricky_recommendations.append(secondary_potential_recommendations[0])

            # 添加主要推荐4（跳过2,3）
            if len(final_primary_recommendations) >= 4:
                tricky_recommendations.append(final_primary_recommendations[3])

            # 添加次要推荐2
            if len(secondary_potential_recommendations) >= 2:
                tricky_recommendations.append(secondary_potential_recommendations[1])

            # 添加主要推荐5
            if len(final_primary_recommendations) >= 5:
                tricky_recommendations.append(final_primary_recommendations[4])

            all_recommendations = tricky_recommendations
            
            # 如果总推荐不足，从剩余候选中补充
            if len(all_recommendations) < 5:
                remaining_candidates = [c['item_id'] for c in candidate_details if c['item_id'] not in all_recommendations]
                all_recommendations.extend(remaining_candidates[:5-len(all_recommendations)])
            
            if self.print_prompts:
                self.safe_print(f"\n🎉 分层需求推荐完成! 总推荐{len(all_recommendations)}个")
                self.safe_print(f"📊 流程: {len(candidate_list)}个候选 → 意图分析 → 主要需求识别与推荐({len(final_primary_recommendations)}) + 次要/潜在需求识别与推荐({len(secondary_potential_recommendations)}) → {len(all_recommendations)}个最终推荐")
                self.safe_print(f"🏆 最终推荐列表: {all_recommendations}")
            
            return {"item_list": all_recommendations}
        
        except Exception as e:
            if self.print_prompts: self.safe_print(f"❌ 分层需求推荐出错: {e}")
            return {"item_list": candidate_list[:5]}
    def _analyze_user_review_style(self, user_reviews: List[Dict], tool) -> Dict[str, Any]:
        if not user_reviews:
            return {"avg_rating": 3.0, "review_count": 0, "avg_text_length": 50, "category_preferences": {}}
        
        ratings = [r['stars'] for r in user_reviews]
        text_lengths = [len(r['text']) for r in user_reviews]
        
        basic_stats = {
            "avg_rating": round(sum(ratings) / len(ratings), 1),
            "review_count": len(user_reviews),
            "avg_text_length": round(sum(text_lengths) / len(text_lengths)),
            "positive_ratio": round(sum(1 for r in ratings if r >= 4) / len(ratings), 2),
        }
        
        category_preferences = {}
        
        for review in user_reviews:
            item_info = tool.get_item(review.get('item_id'))
            if not item_info: continue
            
            category = self._extract_main_category(item_info.get('categories', 'Unknown'))
            if category not in category_preferences:
                category_preferences[category] = {'count': 0, 'ratings': []}
            category_preferences[category]['count'] += 1
            category_preferences[category]['ratings'].append(review['stars'])
        
        for data in category_preferences.values():
            data['avg_rating'] = round(sum(data['ratings']) / len(data['ratings']), 1)
        
        return {**basic_stats, 'category_preferences': category_preferences}

    def _parse_review_response(self, response: str, user_preferences: Dict) -> Dict[str, Any]:
        try:
            result = self._parse_json(response)
            if result.get("stars") and result.get("review"):
                stars = result["stars"]
                if isinstance(stars, int) and 1 <= stars <= 5:
                    review_text = result["review"].strip()
                    max_length = 120
                    if len(review_text) > max_length: review_text = review_text[:max_length-3] + "..."
                    return {"stars": stars, "review": review_text}
        
        except Exception as e:
            if self.print_prompts: self.safe_print(f"评论解析错误: {e}")
        
        default_rating = max(1, min(5, round(user_preferences.get("avg_rating", 3))))
        sentences = [s.strip() for s in response.replace('\n', '. ').split('.') if len(s.strip()) > 20]
        default_review = sentences[0] if sentences else "This place has good quality."
        
        max_length = 120
        if len(default_review) > max_length: default_review = default_review[:max_length-3] + "..."
        
        return {"stars": default_rating, "review": default_review}

    async def _generate_review(self, user_id: str, item_id: str, tool) -> Dict[str, Any]:
        user_reviews = tool.get_reviews(user_id=user_id)
        item_info = tool.get_item(item_id)
        item_reviews = tool.get_reviews(item_id=item_id)
        
        if not item_info: return {"stars": 3, "review": "This place seems decent."}
        
        user_preferences = self._analyze_user_review_style(user_reviews, tool)
        target_category = self._extract_main_category(item_info.get('categories', 'Unknown'))
        item_avg_rating = item_info.get('stars', 0) or (sum(r['stars'] for r in item_reviews) / len(item_reviews) if item_reviews else 3)
        
        # 构建用户偏好摘要
        category_prefs = user_preferences.get('category_preferences', {})
        preference_parts = [
            f"用户评价习惯: 平均{user_preferences.get('avg_rating', 3)}星，共{user_preferences.get('review_count', 0)}条评价",
            f"积极评价比例: {user_preferences.get('positive_ratio', 0)*100:.0f}%"
        ]
        
        if target_category in category_prefs:
            target_stats = category_prefs[target_category]
            preference_parts.append(f"在{target_category}类别: 评价{target_stats['count']}次，平均{target_stats['avg_rating']}星")
        
        preference_summary = "\n".join(preference_parts)
        
        # 获取用户相关评论示例
        candidate_categories = [target_category]
        user_relevant_reviews = self._get_user_relevant_reviews(user_reviews, candidate_categories, tool, limit=5)

        system_prompt = """你是一个评价写手，需要根据用户的历史行为模式为场所写出符合该用户风格的评价。

要求：
1. 评分要符合用户的评分习惯和对该类场所的偏好
2. 评价文本要模仿用户的写作风格，长度控制在30-50词
3. 内容要合理，关注用户历史上重视的场所特征"""

        user_prompt = f"""用户偏好分析：
{preference_summary}

{user_relevant_reviews}

目标场所信息：
- 场所名称: {item_info.get('name', 'Unknown')}
- 场所类别: {target_category}
- 该场所平均评分: {item_avg_rating:.1f}星

请根据用户的偏好模式生成一条评价。

输出格式：
```json
{{
    "stars": [1-5的整数评分],
    "review": "[模仿用户风格的评价文本，30-50词]"
}}
```"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        self._print_prompt(messages, "REVIEW_GENERATION", "Review Generator")
        response = await self.llm.atext_request(messages)
        return self._parse_review_response(response, user_preferences)

    async def forward(self, task_context: dict[str, Any]):
        target = task_context["target"]
        if target == "recommendation":
            return await self._handle_recommendation(task_context)
        elif target == "review_writing":
            user_id, item_id = task_context["user_id"], task_context["item_id"]
            tool = self.toolbox.get_tool_object("uir")
            return await self._generate_review(user_id, item_id, tool)
        else:
            raise ValueError(f"Unknown target: {target}")