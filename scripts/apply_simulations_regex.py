import re

file_path = "c:/Users/cardo/01_Desarrollo/Proyectos_Personales/Sherlock/src/ui/api/compare.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace get_nbinom_under_over_prob definition
pattern = r"def get_nbinom_under_over_prob.*?return p_under \* 100\.0, p_over \* 100\.0, p_push \* 100\.0"

new_get_nb = '''def get_nbinom_under_over_prob(line: float, h_mu: float, h_r: float, a_mu: float, a_r: float, num_sim: int = 10000) -> tuple[float, float, float]:
    h_p = h_r / (h_r + h_mu)
    h_sims = np.random.negative_binomial(h_r, h_p, num_sim)
    
    a_p = a_r / (a_r + a_mu)
    a_sims = np.random.negative_binomial(a_r, a_p, num_sim)
    
    total_sims = h_sims + a_sims
    
    p_under = np.mean(total_sims < line)
    p_push = np.mean(total_sims == line) if line.is_integer() else 0.0
    p_over = 1.0 - float(p_under) - float(p_push)
    
    return float(p_under) * 100.0, float(p_over) * 100.0, float(p_push) * 100.0'''

content = re.sub(pattern, new_get_nb, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Regex replacement script executed.")
