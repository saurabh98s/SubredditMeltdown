# inside your repo folder
while IFS=$'\t' read -r title body labels; do
  [[ "$title" == "Title" ]] && continue

  gh issue create \
      --title "$title" \
      --body  "$body" \
      --label "$labels"
done < project_tasks.tsv
