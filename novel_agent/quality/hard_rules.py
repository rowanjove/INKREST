import re
from typing import Any, Dict, List, Optional
from novel_agent.scripts.count_chars import count_chinese_chars

def run_hard_rule_audit(
    final_text: str,
    state: Dict[str, Any],
    target_chars: List[int],
    sensitive_words: List[str],
    state_update: Optional[Dict[str, Any]] = None,
    plan: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    if final_text is None:
        final_text = ""
    issues = []
    state_update = state_update or {}
    plan = plan or {}
    
    # ----------------------------------------------------
    # 1. 字数字符硬检查
    # ----------------------------------------------------
    char_count = count_chinese_chars(final_text)
    min_chars, max_chars = target_chars[0], target_chars[1]
    if char_count < min_chars or char_count > max_chars:
        issues.append({
            "type": "word_count_out_of_bounds",
            "issue_layer": "text",
            "severity": "high",
            "audit_class": "CRITICAL",
            "text": f"章节字数异常：{char_count} 字",
            "why": f"章节字数 ({char_count}) 偏离了设定范围 {min_chars} - {max_chars}。",
            "fix": "若不足则需要丰富动作和环境细节、扩充对话；若超标则需要删减多余废话铺垫。"
        })

    # ----------------------------------------------------
    # 2. 敏感词硬匹配
    # ----------------------------------------------------
    if sensitive_words:
        escaped = [re.escape(w) for w in sensitive_words if w.strip()]
        if escaped:
            pattern = re.compile("|".join(escaped))
            for line_no, line in enumerate(final_text.splitlines(), start=1):
                for match in pattern.finditer(line):
                    word = match.group()
                    issues.append({
                        "type": "sensitive_word_hit",
                        "issue_layer": "risk",
                        "severity": "high",
                        "audit_class": "CRITICAL",
                        "text": f"敏感词违规：'{word}' (行 {line_no})",
                        "target_text": word,
                        "why": f"本章第 {line_no} 行命中了词库中的发布敏感词：'{word}'。",
                        "fix": f"请使用合规词汇替换该敏感词片段：'{line.strip()}'。"
                    })

    # ----------------------------------------------------
    # 3. 空间位置合理性硬检查
    # ----------------------------------------------------
    characters_state = state.get("characters") or {}
    extracted_char_updates = state_update.get("characters") or {}
    
    # 收集本章所有的期望场景地点
    scenes = plan.get("scenes") or []
    allowed_locations = set()
    for s in scenes:
        loc = s.get("location") or s.get("scene_location")
        if loc:
            allowed_locations.add(loc)
            
    for char_name, info in characters_state.items():
        if not isinstance(info, dict):
            continue
        old_loc = info.get("location")
        if not old_loc:
            continue
            
        # 角色出现在正文中
        if char_name in final_text:
            extracted_loc = None
            char_upd = extracted_char_updates.get(char_name)
            if isinstance(char_upd, dict):
                extracted_loc = char_upd.get("location") or char_upd.get("status")
                
            for scene_loc in allowed_locations:
                if scene_loc == old_loc:
                    continue
                
                # 基于段落的共现检测：如果在该段落内同时提到了该角色和新场景地点
                paragraphs = final_text.split("\n\n")
                char_seen_at_loc = False
                for p in paragraphs:
                    if char_name in p and scene_loc in p:
                        char_seen_at_loc = True
                        break
                
                if char_seen_at_loc:
                    if extracted_loc == scene_loc:
                        continue
                    issues.append({
                        "type": "character_location_mismatch",
                        "issue_layer": "state",
                        "severity": "high",
                        "audit_class": "CRITICAL",
                        "text": f"角色空间越界：{char_name} 的状态与正文脱节",
                        "why": f"角色 {char_name} 历史登记地点为 '{old_loc}'，正文里在 '{scene_loc}' 活动，但 state_update 漏提了此位置移动。",
                        "fix": f"请在正文中交代 {char_name} 前往 '{scene_loc}' 的动作，或在 state_update 中补充该角色的 location 状态更新。"
                    })

    # ----------------------------------------------------
    # 4. 道具持有权硬检查
    # ----------------------------------------------------
    objects_state = state.get("objects") or []
    extracted_object_updates = state_update.get("objects") or []
    
    extracted_holders = {}
    for obj_upd in extracted_object_updates:
        if isinstance(obj_upd, dict) and obj_upd.get("id"):
            new_holder = obj_upd.get("owner") or obj_upd.get("holder")
            if new_holder:
                extracted_holders[obj_upd["id"]] = new_holder
                
    for obj in objects_state:
        if not isinstance(obj, dict) or not obj.get("id"):
            continue
        obj_id = obj["id"]
        obj_name = obj.get("name") or obj_id
        current_holder = obj.get("holder") or obj.get("owner")
        if not current_holder:
            continue
            
        if obj_name in final_text:
            paragraphs = final_text.split("\n\n")
            for p in paragraphs:
                if obj_name in p:
                    for other_char in characters_state.keys():
                        if other_char == current_holder:
                            continue
                        if other_char in p:
                            new_holder = extracted_holders.get(obj_id)
                            if new_holder == other_char:
                                continue
                            
                            issues.append({
                                "type": "object_ownership_conflict",
                                "issue_layer": "state",
                                "severity": "high",
                                "audit_class": "CRITICAL",
                                "text": f"道具使用越权：{obj_name} 的所有者脱节",
                                "why": f"道具 '{obj_name}' 登记在 '{current_holder}' 手中，但正文段落显示 '{other_char}' 正在使用它，且 state_update 漏提了此所有权转移。",
                                "fix": f"请在正文中写明 {other_char} 获得 '{obj_name}' 的情节（如夺取、赠予），或在 state_update 中补全该道具的 owner 状态更新。"
                            })
                            break

    # ----------------------------------------------------
    # 5. 多维指标提取（台词比例）
    # ----------------------------------------------------
    dialogue_chars = 0
    dialogue_matches = re.findall(r"“([^”]*?)”", final_text)
    for dm in dialogue_matches:
        dialogue_chars += len(dm)
        
    total_len = len(final_text.strip())
    if total_len > 0:
        dialogue_ratio = (dialogue_chars / total_len) * 100.0
        if dialogue_ratio > 65.0:
            issues.append({
                "type": "excessive_dialogue",
                "issue_layer": "text",
                "severity": "medium",
                "audit_class": "WARNING",
                "text": f"台词比例过高：{dialogue_ratio:.1f}%",
                "why": f"本章对话台词占比为 {dialogue_ratio:.1f}%，叙述过少，小说感较弱，像剧本。",
                "fix": "减少直白冗长的汇报式台词，增加环境、眼神及肢体动作描写。"
            })
        elif dialogue_ratio < 15.0:
            issues.append({
                "type": "deficient_dialogue",
                "issue_layer": "text",
                "severity": "medium",
                "audit_class": "WARNING",
                "text": f"台词比例过低：{dialogue_ratio:.1f}%",
                "why": f"本章对话台词仅占比 {dialogue_ratio:.1f}%，纯叙述堆砌，节奏沉闷。",
                "fix": "在场景中加入人物语言交流，通过对话打破单调长叙事。"
            })

    return issues
