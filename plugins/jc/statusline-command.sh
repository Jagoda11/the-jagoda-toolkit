#!/bin/bash
input=$(cat)

used=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
remaining=$(echo "$input" | jq -r '.context_window.remaining_percentage // empty')
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
input_tokens=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0')
output_tokens=$(echo "$input" | jq -r '.context_window.total_output_tokens // 0')
cost_usd=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')
model_name=$(echo "$input" | jq -r '.model.display_name // .model.id // empty' | sed -E 's/ *\([^)]*\)//')
dir=$(basename "$cwd")
branch=$(git -C "$cwd" branch --show-current 2>/dev/null)

green=$'\033[32m'; yellow=$'\033[33m'; red=$'\033[31m'; cyan=$'\033[36m'; reset=$'\033[0m'

if [ -n "$used" ]; then
  used_int=$(printf "%.0f" "$used")
  remaining_int=$(printf "%.0f" "${remaining:-$((100 - used_int))}")
  if [ "$used_int" -lt 70 ]; then bar_color="$green"
  elif [ "$used_int" -lt 90 ]; then bar_color="$yellow"
  else bar_color="$red"; fi
  filled=$((used_int / 10)); empty=$((10 - filled)); bar=""
  [ "$filled" -gt 0 ] && printf -v f "%${filled}s" "" && bar="${f// /█}"
  [ "$empty" -gt 0 ] && printf -v p "%${empty}s" "" && bar="${bar}${p// /░}"
  ctx_info="${bar_color}${bar}${reset} ${used_int}% used / ${remaining_int}% left"
else
  ctx_info="ctx: --"
fi

total_tokens=$((input_tokens + output_tokens))
tokens_fmt=$(awk -v t="$total_tokens" 'BEGIN {if (t >= 1000) printf "%.1fk", t/1000; else print t}')
cost_fmt=$(awk -v c="$cost_usd" 'BEGIN { printf "$%.2f", c }')
branch_info=""; [ -n "$branch" ] && branch_info=" | 🌱 ${cyan}${branch}${reset}"

echo -e "${ctx_info}"
echo -e "📁 ${dir}${branch_info}"
model_info=""; [ -n "$model_name" ] && model_info=" | 🤖 ${model_name}"
echo -e "🎫 ${tokens_fmt} | 💰 ${cost_fmt}${model_info}"
