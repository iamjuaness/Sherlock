import re

file_path = "c:/Users/cardo/01_Desarrollo/Proyectos_Personales/Sherlock/src/ui/api/compare.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Insert new math helpers and replace _get_dispersion_r
new_helpers = '''
def _nbinom_pmf(k: int, mu: float, r: float) -> float:
    if mu <= 0 or r <= 0:
        return 1.0 if k == 0 else 0.0
    p = r / (r + mu)
    try:
        log_pmf = (math.lgamma(k + r) - math.lgamma(r) - math.lgamma(k + 1) + 
                   r * math.log(p) + k * math.log(1.0 - p))
        return math.exp(log_pmf)
    except (ValueError, OverflowError):
        return 0.0

def get_nbinom_under_over_prob(line: float, mu: float, r: float) -> tuple[float, float, float]:
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
    return p_under * 100.0, p_over * 100.0, p_push * 100.0

def get_dispersion_r(mu: float, variance: float) -> float:
    if variance <= mu * 1.01:
        return 100.0
    r = (mu ** 2) / (variance - mu)
    return max(0.1, min(r, 100.0))
'''

content = re.sub(
    r"def _get_dispersion_r\(mu: float, league_mean: float, league_var: float\) -> float:.*?return mu / \(fano - 1\.0\)",
    new_helpers.strip(),
    content,
    flags=re.DOTALL
)

content = content.replace(
    "r = _get_dispersion_r(mu, corners_mean / 2.0, max(team_var, corners_mean / 2.0 + 0.01))",
    "r = get_dispersion_r(mu, max(team_var, corners_mean / 2.0 + 0.01))"
)

content = content.replace(
    "r_total = _get_dispersion_r(mu_total, mu_total, max(corners_var, mu_total + 0.01))",
    "r_total = get_dispersion_r(mu_total, max(corners_var, mu_total + 0.01))"
)

content = content.replace(
    "r = _get_dispersion_r(mu, shots_mean / 2.0, max(team_var, shots_mean / 2.0 + 0.01))",
    "r = get_dispersion_r(mu, max(team_var, shots_mean / 2.0 + 0.01))"
)

content = content.replace(
    "return max(lam, 0.4)",
    "mu = max(lam, 0.4)\n    team_var = cards_var / 4.0\n    r = get_dispersion_r(mu, max(team_var, cards_mean / 2.0 + 0.01))\n    return mu, r"
)

old_cards_lambda = '''def _compute_cards_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> float:
    h_lam_cards = _compute_team_cards_lambda(h, a, league, is_home=True, general=general, db=db)
    a_lam_cards = _compute_team_cards_lambda(a, h, league, is_home=False, general=general, db=db)

    lam_cards = h_lam_cards + a_lam_cards

    if lam_cards < 1.0:
        lam_cards = league.avg_cards_per_game

    return lam_cards'''
new_cards_lambda = '''def _compute_cards_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float]:
    h_mu, h_r = _compute_team_cards_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_cards_lambda(a, h, league, is_home=False, general=general, db=db)

    mu_total, r_total = _combine_nb_params(h_mu, h_r, a_mu, a_r)
    
    # 4. Regla especial de seguridad para Tarjetas:
    r_total = max(4.0, r_total)

    if mu_total < 1.0:
        mu_total = league.avg_cards_per_game

    return mu_total, r_total'''
content = content.replace(old_cards_lambda, new_cards_lambda)

content = content.replace(
    "return max(lam, 0.5)",
    "mu = max(lam, 0.5)\n    team_var = sot_var / 4.0\n    r = get_dispersion_r(mu, max(team_var, sot_mean / 2.0 + 0.01))\n    return mu, r"
)

old_sot_lambda = '''def _compute_shots_target_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> float:
    h_st_exp = _compute_team_shots_target_lambda(h, a, league, is_home=True, general=general, db=db)
    a_st_exp = _compute_team_shots_target_lambda(a, h, league, is_home=False, general=general, db=db)
    lam_shots_target = h_st_exp + a_st_exp
    return max(lam_shots_target, league.avg_shots_target_per_game * 0.5)'''
new_sot_lambda = '''def _compute_shots_target_lambda(h: FootballTeamStats, a: FootballTeamStats, league: LeagueStats, general: bool = False, db: Any = None) -> tuple[float, float]:
    h_mu, h_r = _compute_team_shots_target_lambda(h, a, league, is_home=True, general=general, db=db)
    a_mu, a_r = _compute_team_shots_target_lambda(a, h, league, is_home=False, general=general, db=db)
    mu_total, r_total = _combine_nb_params(h_mu, h_r, a_mu, a_r)
    return max(mu_total, league.avg_shots_target_per_game * 0.5), r_total'''
content = content.replace(old_sot_lambda, new_sot_lambda)

content = content.replace(
    "lam_cards        = _compute_cards_lambda(h, a, req.league_stats, general=use_general, db=db)",
    "lam_cards, r_cards_combined = _compute_cards_lambda(h, a, req.league_stats, general=use_general, db=db)"
)
content = content.replace(
    "lam_shots_target = _compute_shots_target_lambda(h, a, req.league_stats, general=use_general, db=db)",
    "lam_shots_target, r_shots_target_combined = _compute_shots_target_lambda(h, a, req.league_stats, general=use_general, db=db)"
)

content = content.replace(
    "p_over, p_push, p_under = _neg_binomial_over_under(lam_corners, line, r_corners_combined)",
    "p_under, p_over, p_push = get_nbinom_under_over_prob(line, lam_corners, r_corners_combined)"
)

old_cards_integ = '''    # ── Over/Under TARJETAS ──────────────────
    cards_mean = req.league_stats.avg_yellow_cards_per_game + (req.league_stats.avg_red_cards_per_game * 2.0) if req.league_stats.avg_yellow_cards_per_game > 0 else req.league_stats.avg_cards_per_game
    cards_var = _estimate_league_variance(req.competition, "cards", cards_mean, db=db)
    r_cards = _get_dispersion_r(lam_cards, cards_mean, cards_var)

    projected_lines.append(ProjectedLine(
        label="Tarjetas Totales (λ)", value=round(lam_cards, 1),
        type="cards", prob=None
    ))
    for line in req.odds.cards_lines:
        p_over, p_push, p_under = _neg_binomial_over_under(lam_cards, line, r_cards)'''

new_cards_integ = '''    # ── Over/Under TARJETAS ──────────────────
    projected_lines.append(ProjectedLine(
        label="Tarjetas Totales (λ)", value=round(lam_cards, 1),
        type="cards", prob=None
    ))
    for line in req.odds.cards_lines:
        p_under, p_over, p_push = get_nbinom_under_over_prob(line, lam_cards, r_cards_combined)'''
content = content.replace(old_cards_integ, new_cards_integ)

content = content.replace(
    "p_over, p_push, p_under = _neg_binomial_over_under(lam_shots, line, r_shots_combined)",
    "p_under, p_over, p_push = get_nbinom_under_over_prob(line, lam_shots, r_shots_combined)"
)

old_sot_integ = '''    # ── Over/Under TIROS A PUERTA ──────────────────
    sot_mean = req.league_stats.avg_shots_target_per_game
    sot_var = _estimate_league_variance(req.competition, "shots_target", sot_mean, db=db)
    r_shots_target = _get_dispersion_r(lam_shots_target, sot_mean, sot_var)

    projected_lines.append(ProjectedLine(
        label="Tiros a Puerta (λ)", value=round(lam_shots_target, 1),
        type="shots_target", prob=None
    ))
    for line in req.odds.shots_target_lines:
        p_over, p_push, p_under = _neg_binomial_over_under(lam_shots_target, line, r_shots_target)'''
new_sot_integ = '''    # ── Over/Under TIROS A PUERTA ──────────────────
    projected_lines.append(ProjectedLine(
        label="Tiros a Puerta (λ)", value=round(lam_shots_target, 1),
        type="shots_target", prob=None
    ))
    for line in req.odds.shots_target_lines:
        p_under, p_over, p_push = get_nbinom_under_over_prob(line, lam_shots_target, r_shots_target_combined)'''
content = content.replace(old_sot_integ, new_sot_integ)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
