"""Recompute course evidence checks without treating templates as completed work."""
import json
import re
from pathlib import Path
from count_code import inventory

root=Path(__file__).resolve().parents[1]
readme=(root/'README.md').read_text()
without_code=re.sub(r'```.*?```','',readme,flags=re.S)
chars=len(re.findall(r'[\u4e00-\u9fff]',without_code))
code=inventory(root)
results=json.loads((root/'examples/reports/system-eval/results.json').read_text())
refs=json.loads((root/'course/references.json').read_text())
checks={
 'readme_chinese_characters':chars,'readme_minimum_met':chars>=2500,
 'readme_sections_present':all(x in readme for x in ['这是什么','怎么装','怎么跑','效果如何','已知问题']),
 'original_backend_lines':code['total_lines'],'nonempty_modules':code['nonempty_modules'],
 'code_minimum_met':code['total_lines']>=800 and code['nonempty_modules']>=3,
 'paired_trials':len(results),'unique_task_arm_pairs':len({(r['task'],r['arm']) for r in results}),
 'system_metrics':['completed','protocol_correct','evidence_complete','wall_seconds'],
 'reference_records':len(refs),'references_2023_or_later':sum(r['year']>=2023 for r in refs),
 'references_have_sources':all(r['url'].startswith('https://') and r.get('verification') for r in refs),
 'required_files_present':all((root/f).is_file() for f in ['LICENSE','backend/requirements.lock.txt','agent/package-lock.json','docs/architecture.md','docs/system-evaluation.md','docs/technical-selection.md','docs/docker-release-020.md']),
 'author_pending':['official_cover_and_identity','personal_reflection_and_conclusions','self_assessment','signed_AI_declaration','video','external_user_validation','final_submission_pdf_and_plagiarism_check']}
assert checks['readme_minimum_met'] and checks['readme_sections_present'] and checks['code_minimum_met']
assert checks['paired_trials']==checks['unique_task_arm_pairs']==20
assert checks['reference_records']>=15 and checks['references_2023_or_later']/len(refs)>=.6
assert checks['required_files_present'] and checks['references_have_sources']
print(json.dumps(checks,ensure_ascii=False,indent=2))
