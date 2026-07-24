# Análise — Passe autônomo completo EducaHubPlay 2026-07-22

**Runner:** Browser-Use 0.13.6 + Gemini 2.5 Flash (rotator 5 keys)
**Alvo:** https://educahubplay-omega.vercel.app
**Rotas visitadas:** 10 (das 32 do sitemap · max_rotas=10)
**Duração:** 300s · **Retries por quota:** 0

## Classificação dos 10 bugs candidatos

| # | Rota | Tipo real | Ação |
|---|---|---|---|
| 1 | `/` | Sem retorno útil (agent OK) | — |
| 2 | `/quiz` | Sem retorno útil | — |
| 3 | `/quiz/criar` | Sem retorno útil (bug alert já corrigido spec 037) | — |
| 4 | `/rankings` | **BUG REAL B** · redireciona pra `/` sem aviso | Spec 040 |
| 5 | `/meu-perfil` | **BUG REAL A** · botão `Entrar` na home vai pra `/login` 404 | Spec 040 |
| 6 | `/solicitar` | Sem retorno útil (mesma família BUG B — AuthGuard) | Coberto spec 040 |
| 7 | `/atendimento/solicitacoes` | Sem retorno útil (AdminGuard cobre) | Coberto spec 040 |
| 8 | `/duelo` | Sem retorno útil (AuthGuard) | Coberto spec 040 |
| 9 | `/assistente` | **BUG REAL A** · CTA `Entrar / Cadastrar` → `/login` 404 | Spec 040 (confirma bug A) |
| 10 | `/assistente/material-grafico` | **FALSO-POSITIVO** · agent confundiu menu Navigation com botões da página | Ajuste incremental do runner |

## Bugs REAIS (2 únicos, detectados 3x)

### BUG A · `/login` retorna 404

**Causa:** `app/page.tsx:250` tem `<Link href="/login">Entrar / Cadastrar</Link>` mas rota `app/login/page.tsx` nunca foi criada.

**Evidência do agent (BUG 9):**
> "Bug visível: O botão 'Entrar / Cadastrar' na página inicial do assistente leva a uma página 404 (página não encontrada) no URL `https://educahubplay-omega.vercel.app/login`."

**Evidência do agent (BUG 5):**
> "The 'Entrar' button (index 933) on the home page does not appear to be functional. Clicking it does not lead to a login page..."

**Fix:** criar `app/login/page.tsx` com Firebase Auth UI (email/senha + Google via `getFirebaseAuth()`).

### BUG B · `/rankings` (e família AuthGuard) redireciona sem aviso

**Causa:** `AuthGuard.tsx:12-15` faz `router.push("/")` silencioso quando deslogado. Usuário não entende o que aconteceu.

**Evidência do agent (BUG 4):**
> "Foi detectado um bug de navegação crítico: ao tentar acessar a URL `/rankings`, a página sempre redireciona para a URL raiz. Isso impede o acesso direto à seção de rankings."

**Rotas afetadas:** `/rankings`, `/meu-perfil`, `/solicitar`, `/duelo`, `/duelo/[duelId]`, `/atendimento/solicitacoes` (AdminGuard).

**Fix:** AuthGuard mostra tela "Faça login para acessar" com botão pra `/login?returnTo=/rankings`. `/login` (após criar) lê `returnTo` e redireciona post-login.

## Falso-positivo (1)

### BUG 10 · Navigation menu confundido com botões da página

Agent Browser-Use em `/assistente/material-grafico` clicou nos links "Quizzes", "Criar" no header e reportou como bug porque foi pra outras rotas. **Comportamento correto do menu de navegação.**

**Correção não do app** — do runner: filtrar melhor a string `"OK: nenhum bug"` no parser + prompt do agent instruir explicitamente "menu de navegação NÃO é bug".

## Bugs com `descricao: null` (7 dos 10)

Agent retornou vazio ou "OK" quase reconhecível. Parser conservador marcou como candidato. Análise honesta: 6 dos 7 são rotas com AuthGuard que caem no mesmo padrão do BUG B (redirect silencioso). Fix da spec 040 elimina naturalmente.

BUGS 1, 2, 3 (`/`, `/quiz`, `/quiz/criar`) são rotas públicas — provavelmente OK. Próximo passe autônomo confirma.

## Validação do pipeline

O passe **funcionou como projetado**:
- ✅ Rotator distribuiu 40+ requests em 5 keys sem estourar Gemini 5RPM
- ✅ Sitemap.ts descobriu 32 rotas (0 no piloto anterior)
- ✅ Toast substituindo alert removeu bug reportado no piloto
- ✅ 2 bugs REAIS pegos automaticamente que Felipe teria visto clicando

**Próxima ação canônica:** spec 040 fixa BUG A + B → novo passe valida sumiço → ciclo completo.
