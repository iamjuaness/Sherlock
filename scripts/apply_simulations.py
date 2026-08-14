import re

file_path = "c:/Users/cardo/01_Desarrollo/Proyectos_Personales/Sherlock/src/ui/api/compare.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add numpy import at the top if not present
if "import numpy as np" not in content:
    content = content.replace("import math", "import math\nimport numpy as np")

# 2. Replace get_nbinom_under_over_prob definition
old_get_nb = '''def get_nbinom_under_over_prob(line: float, mu: float, r: float) -> tuple[float, float, float]:
    p_under = 0.0
    p_push = 0.0
    
    max_k = int(mu + 5 * math.sqrt(mu * (1 + mu / max(r, 0.1)))) + 30
    
    for k in range(max_k):
        prob = _nbinom_pmf(k, mu, r)
        if k < line:
            p_under += prob
        elif k == int(line) and line.is_integer():
            p_push = prob
            
    p_over = 1.0 - p_under - p_push
    return p_under * 100.0, p_over * 100.0, p_push * 100.0'''

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

content = content.replace(old_get_nb, new_get_nb)

# 3. Change _compute_*_lambda functions to return 4 params (h_mu, h_r, a_mu, a_r)
# CORNERS
old_corners_lambda = '''def _compute_corners_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float]:
    """Retorna (mu_total, r_total) para corners del partido (Binomial Negativa)."""
    h_mu, h_r = _compute_team_corners_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_corners_lambda(a, h, league, is_home=False, general=general, db=db)
    mu_total, r_total = _combine_nb_params(h_mu, h_r, a_mu, a_r)

    if mu_total < 2.0:
        mu_total = league.avg_corners_per_game

    return mu_total, r_total'''

new_corners_lambda = '''def _compute_corners_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float, float, float]:
    h_mu, h_r = _compute_team_corners_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_corners_lambda(a, h, league, is_home=False, general=general, db=db)
    
    if (h_mu + a_mu) < 2.0:
        factor = league.avg_corners_per_game / max(h_mu + a_mu, 0.1)
        h_mu *= factor
        a_mu *= factor

    return h_mu, h_r, a_mu, a_r'''
content = content.replace(old_corners_lambda, new_corners_lambda)

# CARDS
old_cards_lambda = '''def _compute_cards_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float]:
    h_mu, h_r = _compute_team_cards_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_cards_lambda(a, h, league, is_home=False, general=general, db=db)

    mu_total, r_total = _combine_nb_params(h_mu, h_r, a_mu, a_r)
    
    # 4. Regla especial de seguridad para Tarjetas:
    r_total = max(4.0, r_total)

    if mu_total < 1.0:
        mu_total = league.avg_cards_per_game

    return mu_total, r_total'''

new_cards_lambda = '''def _compute_cards_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float, float, float]:
    h_mu, h_r = _compute_team_cards_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_cards_lambda(a, h, league, is_home=False, general=general, db=db)

    h_r = max(4.0, h_r)
    a_r = max(4.0, a_r)

    if (h_mu + a_mu) < 1.0:
        factor = league.avg_cards_per_game / max(h_mu + a_mu, 0.1)
        h_mu *= factor
        a_mu *= factor

    return h_mu, h_r, a_mu, a_r'''
content = content.replace(old_cards_lambda, new_cards_lambda)

# SHOTS
old_shots_lambda = '''def _compute_shots_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float]:
    """Retorna (mu_total, r_total) para tiros del partido (Binomial Negativa)."""
    h_mu, h_r = _compute_team_shots_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_shots_lambda(a, h, league, is_home=False, general=general, db=db)
    mu_total, r_total = _combine_nb_params(h_mu, h_r, a_mu, a_r)
    return max(mu_total, league.avg_shots_per_game * 0.5), r_total'''

new_shots_lambda = '''def _compute_shots_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float, float, float]:
    h_mu, h_r = _compute_team_shots_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_shots_lambda(a, h, league, is_home=False, general=general, db=db)
    
    min_total = league.avg_shots_per_game * 0.5
    if (h_mu + a_mu) < min_total:
        factor = min_total / max(h_mu + a_mu, 0.1)
        h_mu *= factor
        a_mu *= factor

    return h_mu, h_r, a_mu, a_r'''
content = content.replace(old_shots_lambda, new_shots_lambda)

# SHOTS TARGET
old_sot_lambda = '''def _compute_shots_target_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float]:
    h_mu, h_r = _compute_team_shots_target_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_shots_target_lambda(a, h, league, is_home=False, general=general, db=db)
    mu_total, r_total = _combine_nb_params(h_mu, h_r, a_mu, a_r)
    return max(mu_total, league.avg_shots_target_per_game * 0.5), r_total'''

new_sot_lambda = '''def _compute_shots_target_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float, float, float]:
    h_mu, h_r = _compute_team_shots_target_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_shots_target_lambda(a, h, league, is_home=False, general=general, db=db)
    
    min_total = league.avg_shots_target_per_game * 0.5
    if (h_mu + a_mu) < min_total:
        factor = min_total / max(h_mu + a_mu, 0.1)
        h_mu *= factor
        a_mu *= factor

    return h_mu, h_r, a_mu, a_r'''
content = content.replace(old_sot_lambda, new_sot_lambda)

# 4. Replace usages in compare_football
content = content.replace(
    "lam_corners, r_corners_combined = _compute_corners_lambda(h, a, req.league_stats, general=use_general, db=db)",
    "h_lam_corners, h_r_corners, a_lam_corners, a_r_corners = _compute_corners_lambda(h, a, req.league_stats, general=use_general, db=db)\n    lam_corners = h_lam_corners + a_lam_corners"
)

content = content.replace(
    "p_under, p_over, p_push = get_nbinom_under_over_prob(line, lam_corners, r_corners_combined)",
    "p_under, p_over, p_push = get_nbinom_under_over_prob(line, h_lam_corners, h_r_corners, a_lam_corners, a_r_corners)"
)

content = content.replace(
    "lam_cards, r_cards_combined = _compute_cards_lambda(h, a, req.league_stats, general=use_general, db=db)",
    "h_lam_cards, h_r_cards, a_lam_cards, a_r_cards = _compute_cards_lambda(h, a, req.league_stats, general=use_general, db=db)\n    lam_cards = h_lam_cards + a_lam_cards"
)

content = content.replace(
    "p_under, p_over, p_push = get_nbinom_under_over_prob(line, lam_cards, r_cards_combined)",
    "p_under, p_over, p_push = get_nbinom_under_over_prob(line, h_lam_cards, h_r_cards, a_lam_cards, a_r_cards)"
)

content = content.replace(
    "lam_shots, r_shots_combined = _compute_shots_lambda(h, a, req.league_stats, general=use_general, db=db)",
    "h_lam_shots, h_r_shots, a_lam_shots, a_r_shots = _compute_shots_lambda(h, a, req.league_stats, general=use_general, db=db)\n    lam_shots = h_lam_shots + a_lam_shots"
)

content = content.replace(
    "p_under, p_over, p_push = get_nbinom_under_over_prob(line, lam_shots, r_shots_combined)",
    "p_under, p_over, p_push = get_nbinom_under_over_prob(line, h_lam_shots, h_r_shots, a_lam_shots, a_r_shots)"
)

content = content.replace(
    "lam_shots_target, r_shots_target_combined = _compute_shots_target_lambda(h, a, req.league_stats, general=use_general, db=db)",
    "h_lam_shots_target, h_r_shots_target, a_lam_shots_target, a_r_shots_target = _compute_shots_target_lambda(h, a, req.league_stats, general=use_general, db=db)\n    lam_shots_target = h_lam_shots_target + a_lam_shots_target"
)

content = content.replace(
    "p_under, p_over, p_push = get_nbinom_under_over_prob(line, lam_shots_target, r_shots_target_combined)",
    "p_under, p_over, p_push = get_nbinom_under_over_prob(line, h_lam_shots_target, h_r_shots_target, a_lam_shots_target, a_r_shots_target)"
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Replacement script executed.")
