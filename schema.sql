--
-- PostgreSQL database dump
--

-- Dumped from database version 17.4
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: update_scorers_from_goals(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_scorers_from_goals() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    player_league_id INTEGER;
    player_season_id INTEGER;
    next_scorer_id INTEGER;
BEGIN
    -- Get the league_id and season_id for the player from the match
    SELECT m.league_id, m.season_id INTO player_league_id, player_season_id
    FROM matches m
    WHERE m.match_id = NEW.match_id;
    
    -- Check if a scorer record already exists for this player in this league and season
    IF NOT EXISTS (
        SELECT 1 FROM scorers 
        WHERE player_id = NEW.player_id 
        AND league_id = player_league_id 
        AND season_id = player_season_id
    ) THEN
        -- Find the next available scorer_id
        SELECT COALESCE(MAX(scorer_id), 0) + 1 INTO next_scorer_id FROM scorers;
        
        -- Insert a new scorer record with the next available ID
        INSERT INTO scorers (scorer_id, player_id, league_id, season_id, goals, assists, penalties)
        VALUES (
            next_scorer_id,
            NEW.player_id, 
            player_league_id, 
            player_season_id, 
            CASE WHEN NEW.is_own_goal THEN 0 ELSE 1 END, 
            0, 
            CASE WHEN NEW.is_penalty THEN 1 ELSE 0 END
        );
    ELSE
        -- Update existing scorer record
        UPDATE scorers 
        SET goals = goals + CASE WHEN NEW.is_own_goal THEN 0 ELSE 1 END,
            penalties = penalties + CASE WHEN NEW.is_penalty THEN 1 ELSE 0 END
        WHERE player_id = NEW.player_id 
        AND league_id = player_league_id 
        AND season_id = player_season_id;
    END IF;
    
    RETURN NEW;
END;
$$;


--
-- Name: coaches_coach_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.coaches_coach_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: coaches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.coaches (
    coach_id integer DEFAULT nextval('public.coaches_coach_id_seq'::regclass) NOT NULL,
    name character varying(255) NOT NULL,
    team_id integer,
    nationality character varying(100)
);


--
-- Name: countries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.countries (
    country_id integer NOT NULL,
    name character varying(255) NOT NULL,
    flag_url character varying(255)
);


--
-- Name: goals; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.goals (
    goal_id integer NOT NULL,
    match_id integer,
    player_id integer,
    team_id integer,
    minute integer,
    is_penalty boolean DEFAULT false,
    is_own_goal boolean DEFAULT false,
    is_half_time_goal boolean DEFAULT false
);


--
-- Name: goals_goal_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.goals_goal_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: goals_goal_id_seq1; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.goals_goal_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: goals_goal_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.goals_goal_id_seq1 OWNED BY public.goals.goal_id;


--
-- Name: leagues; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leagues (
    league_id integer NOT NULL,
    name character varying(255) NOT NULL,
    country character varying(255) NOT NULL,
    country_id integer,
    icon_url character varying(255),
    cl_spot integer,
    uel_spot integer,
    relegation_spot integer
);


--
-- Name: match_referees; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.match_referees (
    match_id integer NOT NULL,
    referee_id integer NOT NULL
);


--
-- Name: matches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.matches (
    match_id integer NOT NULL,
    season_id integer,
    league_id integer,
    matchday integer,
    home_team_id integer,
    away_team_id integer,
    winner character varying(50),
    utc_date date,
    stadium_id integer,
    status character varying(50)
);


--
-- Name: matches_match_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.matches_match_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: matches_match_id_seq1; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.matches_match_id_seq1
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: matches_match_id_seq1; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.matches_match_id_seq1 OWNED BY public.matches.match_id;


--
-- Name: password_resets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_resets (
    user_id integer NOT NULL,
    token character varying(255) NOT NULL,
    expires_at timestamp without time zone NOT NULL
);


--
-- Name: players_player_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.players_player_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: players; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.players (
    player_id integer DEFAULT nextval('public.players_player_id_seq'::regclass) NOT NULL,
    team_id integer,
    name character varying(255) NOT NULL,
    "position" character varying(50),
    date_of_birth date,
    nationality character varying(100),
    image_url character varying(255)
);


--
-- Name: playoff_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.playoff_configs (
    config_id integer NOT NULL,
    league_id integer,
    season_id integer,
    num_qualifying_teams integer DEFAULT 4,
    status character varying(20) DEFAULT 'NOT_STARTED'::character varying,
    champion_team_id integer
);


--
-- Name: playoff_configs_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.playoff_configs_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: playoff_configs_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.playoff_configs_config_id_seq OWNED BY public.playoff_configs.config_id;


--
-- Name: playoff_matches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.playoff_matches (
    playoff_match_id integer NOT NULL,
    match_id integer,
    config_id integer,
    round_name character varying(50),
    round_order integer,
    next_match_id integer,
    team_position character varying(20)
);


--
-- Name: playoff_matches_playoff_match_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.playoff_matches_playoff_match_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: playoff_matches_playoff_match_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.playoff_matches_playoff_match_id_seq OWNED BY public.playoff_matches.playoff_match_id;


--
-- Name: referees; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.referees (
    referee_id integer NOT NULL,
    name character varying(255) NOT NULL,
    nationality character varying(100)
);


--
-- Name: scorers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scorers (
    scorer_id integer NOT NULL,
    player_id integer,
    league_id integer,
    season_id integer,
    goals integer DEFAULT 0,
    assists integer DEFAULT 0,
    penalties integer DEFAULT 0
);


--
-- Name: scorers_scorer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scorers_scorer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scores (
    score_id integer NOT NULL,
    match_id integer,
    home_score integer,
    away_score integer,
    home_team_id integer,
    away_team_id integer,
    full_time_home integer,
    full_time_away integer,
    half_time_home integer,
    half_time_away integer
);


--
-- Name: scores_score_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scores_score_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scores_score_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scores_score_id_seq OWNED BY public.scores.score_id;


--
-- Name: seasons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seasons (
    season_id integer NOT NULL,
    name character varying(255) NOT NULL,
    start_date date,
    end_date date,
    league_id integer
);


--
-- Name: stadiums; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stadiums (
    stadium_id integer NOT NULL,
    name character varying(255) NOT NULL,
    city character varying(255),
    country character varying(255),
    capacity integer,
    location character varying(255)
);


--
-- Name: standings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.standings (
    standing_id integer NOT NULL,
    league_id integer,
    team_id integer,
    "position" integer,
    played_games integer,
    won integer,
    draw integer,
    lost integer,
    points integer,
    goals_for integer,
    goals_against integer,
    goal_difference integer,
    form character varying(255)
);


--
-- Name: teams_team_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.teams_team_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: teams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.teams (
    team_id integer DEFAULT nextval('public.teams_team_id_seq'::regclass) NOT NULL,
    name character varying(255) NOT NULL,
    founded_year integer,
    league_id integer,
    stadium_id integer,
    coach_id integer,
    logo_url character varying(255)
);


--
-- Name: users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    user_id integer DEFAULT nextval('public.users_user_id_seq'::regclass) NOT NULL,
    username character varying(255) NOT NULL,
    password character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    is_admin boolean DEFAULT false
);


--
-- Name: goals goal_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goals ALTER COLUMN goal_id SET DEFAULT nextval('public.goals_goal_id_seq1'::regclass);


--
-- Name: matches match_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches ALTER COLUMN match_id SET DEFAULT nextval('public.matches_match_id_seq1'::regclass);


--
-- Name: playoff_configs config_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.playoff_configs ALTER COLUMN config_id SET DEFAULT nextval('public.playoff_configs_config_id_seq'::regclass);


--
-- Name: playoff_matches playoff_match_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.playoff_matches ALTER COLUMN playoff_match_id SET DEFAULT nextval('public.playoff_matches_playoff_match_id_seq'::regclass);


--
-- Name: scores score_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores ALTER COLUMN score_id SET DEFAULT nextval('public.scores_score_id_seq'::regclass);


--
-- Data for Name: coaches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.coaches (coach_id, name, team_id, nationality) FROM stdin;
1	Juan Ferrando	1	Spain
2	Sergio Lobera	2	Spain
3	Simon Grayson	3	England
4	Ivan Vukomanovic	4	Serbia
5	Des Buckingham	5	England
6	Manolo Marquez	6	Spain
7	Manolo Marquez	7	Spain
8	Juan Pedro Benali	8	Spain
9	Carles Cuadrat	9	Spain
10	Scott Cooper	10	England
11	Owen Coyle	11	Scotland
12	Staikos Vergetis	12	Greece
13	Domingo Oramas	13	Spain
14	Fernando Santiago Varela	14	Spain
15	Leimapokpam Nandakumar Singh	15	India
\.


--
-- Data for Name: countries; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.countries (country_id, name, flag_url) FROM stdin;
1	India	/static/images/flags/india.png
2	Spain	/static/images/flags/Spain.png
3	Brazil	/static/images/flags/brazil.png
4	Australia	/static/images/flags/australia.png
5	Nigeria	/static/images/flags/nigeria.png
6	Morocco	/static/images/flags/morocco.png
7	England	/static/images/flags/england.png
8	Scotland	/static/images/flags/scotland.png
9	Greece	/static/images/flags/greece.png
10	Uruguay	/static/images/flags/uruguay.png
11	Fiji	/static/images/flags/fiji.png
12	Croatia	/static/images/flags/croatia.png
13	Uzbekistan	/static/images/flags/uzbekistan.png
14	Portugal	/static/images/flags/portugal.png
15	Argentina	/static/images/flags/agentina.png
\.


--
-- Data for Name: goals; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.goals (goal_id, match_id, player_id, team_id, minute, is_penalty, is_own_goal, is_half_time_goal) FROM stdin;
1	1	32	1	23	f	f	f
2	1	33	1	56	f	f	f
3	1	32	1	67	t	f	f
4	1	19	9	78	f	f	f
5	2	38	4	34	f	f	f
6	2	9	4	62	t	f	f
7	2	11	5	81	f	f	f
8	7	32	1	15	f	f	f
9	7	33	1	43	f	f	f
10	7	38	4	55	f	f	f
11	7	9	4	87	t	f	f
12	8	11	5	13	f	f	f
13	8	40	5	37	f	f	f
14	8	11	5	56	f	f	f
15	8	11	5	78	t	f	f
16	15	44	7	15	f	f	f
17	15	19	9	25	f	f	f
18	15	14	7	35	f	f	f
19	15	19	9	55	t	f	f
\.


--
-- Data for Name: leagues; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.leagues (league_id, name, country, country_id, icon_url, cl_spot, uel_spot, relegation_spot) FROM stdin;
1	Indian Super League	India	1	/static/images/leagues/isl.png	\N	\N	\N
2	I-League	India	1	/static/images/leagues/i_league.png	\N	\N	\N
3	Santosh Trophy	India	1	/static/images/leagues/santosh_trophy.png	\N	\N	\N
4	Durand Cup	India	1	/static/images/leagues/durand_cup.png	\N	\N	\N
5	Super Cup	India	1	/static/images/leagues/super_cup.png	\N	\N	\N
\.


--
-- Data for Name: match_referees; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.match_referees (match_id, referee_id) FROM stdin;
1	1
2	2
3	3
4	4
5	5
6	6
7	7
8	8
9	9
10	10
11	1
12	2
13	3
14	4
15	5
16	6
17	7
18	8
19	9
20	10
21	1
22	2
23	3
\.


--
-- Data for Name: matches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.matches (match_id, season_id, league_id, matchday, home_team_id, away_team_id, winner, utc_date, stadium_id, status) FROM stdin;
1	1	1	\N	1	9	\N	2023-09-23	2	FINISHED
2	1	1	\N	4	5	\N	2023-09-24	1	FINISHED
3	1	1	\N	3	6	\N	2023-09-30	3	FINISHED
4	1	1	\N	7	10	\N	2023-10-01	5	FINISHED
5	1	1	\N	8	11	\N	2023-10-07	7	FINISHED
6	1	1	\N	2	12	\N	2023-10-08	10	FINISHED
7	1	1	\N	1	4	\N	2023-10-14	2	FINISHED
8	1	1	\N	5	3	\N	2023-10-15	4	FINISHED
9	1	1	\N	6	7	\N	2023-10-21	6	FINISHED
10	1	1	\N	9	8	\N	2023-10-22	2	FINISHED
11	1	1	\N	10	2	\N	2023-10-28	8	FINISHED
12	1	1	\N	11	12	\N	2023-10-29	11	FINISHED
13	1	1	\N	4	3	\N	2023-11-04	1	FINISHED
14	1	1	\N	5	6	\N	2023-11-05	4	FINISHED
15	1	1	\N	7	9	\N	2023-11-11	5	FINISHED
16	1	1	\N	8	10	\N	2023-11-12	7	FINISHED
17	1	1	\N	2	11	\N	2023-11-18	10	FINISHED
18	1	1	\N	12	1	\N	2023-11-19	13	FINISHED
19	1	1	\N	3	7	\N	2023-11-25	3	FINISHED
20	1	1	\N	6	8	\N	2023-11-26	6	FINISHED
21	1	1	\N	9	2	\N	2023-12-02	2	FINISHED
22	1	1	\N	10	12	\N	2023-12-03	8	FINISHED
23	1	1	\N	11	1	\N	2023-12-09	11	FINISHED
24	1	1	\N	4	6	\N	2023-12-10	1	SCHEDULED
\.


--
-- Data for Name: password_resets; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.password_resets (user_id, token, expires_at) FROM stdin;
\.


--
-- Data for Name: players; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.players (player_id, team_id, name, "position", date_of_birth, nationality, image_url) FROM stdin;
1	3	Sunil Chhetri	Forward	1984-08-03	India	/static/images/players/sunilchetri.png
2	1	Dimitri Petratos	Forward	1992-11-10	Australia	\N
3	1	Jason Cummings	Forward	1995-08-01	Australia	\N
4	2	Cleiton Silva	Forward	1987-02-11	Brazil	\N
5	2	Nandhakumar Sekar	Midfielder	1996-07-14	India	\N
6	3	Javi Hernandez	Midfielder	1989-06-12	Spain	\N
7	3	Roy Krishna	Forward	1987-08-30	Fiji	\N
8	4	Adrian Luna	Midfielder	1992-04-12	Uruguay	\N
9	4	Dimitrios Diamantakos	Forward	1993-03-05	Greece	\N
10	5	Jorge Pereyra Diaz	Forward	1990-09-19	Argentina	\N
11	5	Lallianzuala Chhangte	Forward	1997-06-08	India	\N
12	6	Bartholomew Ogbeche	Forward	1984-10-01	Nigeria	\N
13	6	Chinglensana Singh	Defender	1996-11-27	India	\N
14	7	Brandon Fernandes	Midfielder	1994-09-20	India	\N
15	7	Boris Singh	Midfielder	2000-03-06	India	\N
16	8	Rahim Ali	Forward	2000-04-21	India	\N
17	8	Farukh Choudhary	Forward	1996-11-08	India	\N
18	9	TP Rehenesh	Goalkeeper	1993-05-01	India	\N
19	9	Peter Hartley	Defender	1988-04-03	England	\N
20	10	Parthib Gogoi	Forward	2002-10-15	India	\N
21	10	Mohammed Irshad	Midfielder	1992-03-25	India	\N
22	11	Jerry Mawihmingthanga	Forward	1997-03-08	India	\N
23	11	Ahmed Jahouh	Midfielder	1988-06-30	Morocco	\N
24	12	Luka Majcen	Forward	1989-05-19	Slovenia	\N
25	12	Suresh Singh Wangjam	Midfielder	2000-08-07	India	\N
26	13	Sreekuttan VS	Forward	2001-05-25	India	\N
27	13	Noufal PN	Midfielder	1997-03-18	India	\N
28	14	Kean Lewis	Midfielder	1992-08-19	India	\N
29	14	Mirjalol Kasimov	Forward	2000-09-21	Uzbekistan	\N
30	15	Tiddim Road Athletic Union	Forward	1993-12-10	Spain	\N
31	15	Ponif Vaz	Defender	1992-05-06	India	\N
32	1	Liston Colaco	Forward	1998-11-12	India	\N
33	1	Manvir Singh	Forward	1995-11-07	India	\N
34	2	Saul Crespo	Midfielder	1996-02-27	Spain	\N
35	2	Harmanjot Khabra	Defender	1988-06-18	India	\N
36	3	Gurpreet Singh Sandhu	Goalkeeper	1992-02-03	India	\N
37	3	Rahul Bheke	Defender	1990-12-06	India	\N
38	4	Jeakson Singh	Midfielder	2001-06-06	India	\N
39	4	Danish Farooq	Midfielder	1996-05-09	India	\N
40	5	Greg Stewart	Forward	1990-03-17	Scotland	\N
41	5	Rahul Bheke	Defender	1990-12-06	India	\N
42	6	Javier Siverio	Forward	1997-06-14	Spain	\N
43	6	Joel Chianese	Forward	1990-02-09	Australia	\N
44	7	Noah Sadaoui	Forward	1993-09-19	Morocco	\N
45	7	Rowllin Borges	Midfielder	1992-06-05	India	\N
46	13	Sreekuttan VS	Forward	2001-05-25	India	\N
47	13	Noufal PN	Midfielder	1997-03-18	India	\N
48	14	Kean Lewis	Midfielder	1992-08-19	India	\N
49	14	Mirjalol Kasimov	Forward	2000-09-21	Uzbekistan	\N
50	15	Tiddim Road Athletic Union	Forward	1993-12-10	Spain	\N
51	15	Ponif Vaz	Defender	1992-05-06	India	\N
52	1	Liston Colaco	Forward	1998-11-12	India	\N
53	1	Manvir Singh	Forward	1995-11-07	India	\N
54	2	Saul Crespo	Midfielder	1996-02-27	Spain	\N
55	2	Harmanjot Khabra	Defender	1988-06-18	India	\N
56	3	Gurpreet Singh Sandhu	Goalkeeper	1992-02-03	India	\N
57	3	Rahul Bheke	Defender	1990-12-06	India	\N
58	4	Jeakson Singh	Midfielder	2001-06-06	India	\N
59	4	Danish Farooq	Midfielder	1996-05-09	India	\N
60	5	Greg Stewart	Forward	1990-03-17	Scotland	\N
61	5	Rahul Bheke	Defender	1990-12-06	India	\N
62	6	Javier Siverio	Forward	1997-06-14	Spain	\N
63	6	Joel Chianese	Forward	1990-02-09	Australia	\N
64	7	Noah Sadaoui	Forward	1993-09-19	Morocco	\N
65	7	Rowllin Borges	Midfielder	1992-06-05	India	\N
\.


--
-- Data for Name: playoff_configs; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.playoff_configs (config_id, league_id, season_id, num_qualifying_teams, status, champion_team_id) FROM stdin;
\.


--
-- Data for Name: playoff_matches; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.playoff_matches (playoff_match_id, match_id, config_id, round_name, round_order, next_match_id, team_position) FROM stdin;
\.


--
-- Data for Name: referees; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.referees (referee_id, name, nationality) FROM stdin;
1	Crystal John	India
2	Tejas Nagvenkar	India
3	Rahul Kumar Gupta	India
4	Rowan Arumughan	India
5	Umesh Bora	India
6	Harish Kundu	India
7	Venkatesh R	India
8	Aditya Purkayastha	India
9	Santosh Kumar	India
10	Pranjal Banerjee	India
\.


--
-- Data for Name: scorers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.scorers (scorer_id, player_id, league_id, season_id, goals, assists, penalties) FROM stdin;
1	1	1	1	11	3	2
2	2	1	1	13	7	4
3	9	1	1	14	2	3
4	11	1	1	10	6	0
5	12	1	1	9	2	3
6	19	1	1	2	0	1
7	44	1	1	1	0	0
8	14	1	1	1	0	0
\.


--
-- Data for Name: scores; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.scores (score_id, match_id, home_score, away_score, home_team_id, away_team_id, full_time_home, full_time_away, half_time_home, half_time_away) FROM stdin;
1	1	\N	\N	1	9	3	1	1	0
2	2	\N	\N	4	5	2	1	1	0
3	3	\N	\N	3	6	2	2	1	1
4	4	\N	\N	7	10	3	0	1	0
5	5	\N	\N	8	11	1	3	0	1
6	6	\N	\N	2	12	4	0	2	0
7	7	\N	\N	1	4	2	2	1	1
8	8	\N	\N	5	3	4	0	2	0
9	9	\N	\N	6	7	1	0	0	0
10	10	\N	\N	9	8	2	1	1	0
11	11	\N	\N	10	2	1	3	0	1
12	12	\N	\N	11	12	5	1	2	0
13	13	\N	\N	4	3	1	0	0	0
14	14	\N	\N	5	6	3	2	1	1
15	15	\N	\N	7	9	2	2	1	1
16	16	\N	\N	8	10	0	1	0	0
17	17	\N	\N	2	11	2	3	1	2
18	18	\N	\N	12	1	0	4	0	2
19	19	\N	\N	3	7	3	1	1	0
20	20	\N	\N	6	8	2	0	1	0
21	21	\N	\N	9	2	1	1	0	0
22	22	\N	\N	10	12	2	0	1	0
23	23	\N	\N	11	1	2	3	1	1
\.


--
-- Data for Name: seasons; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.seasons (season_id, name, start_date, end_date, league_id) FROM stdin;
1	2023/2024 ISL	2023-09-01	2024-05-31	1
2	2023/2024 I-League	2023-10-28	2024-04-30	2
3	2023/2024 Santosh Trophy	2023-12-01	2024-03-31	3
4	2023 Durand Cup	2023-07-28	2023-09-03	4
5	2023 Super Cup	2023-04-08	2023-04-25	5
\.


--
-- Data for Name: stadiums; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.stadiums (stadium_id, name, city, country, capacity, location) FROM stdin;
1	Jawaharlal Nehru Stadium	Kochi	India	55000	Kochi, India
2	Salt Lake Stadium	Kolkata	India	68000	Kolkata, India
3	Sree Kanteerava Stadium	Bangalore	India	25000	Bangalore, India
4	Mumbai Football Arena	Mumbai	India	8000	Mumbai, India
5	Fatorda Stadium	Margao	India	19000	Margao, India
6	GMC Balayogi Athletic Stadium	Hyderabad	India	30000	Hyderabad, India
7	Indira Gandhi Athletic Stadium	Guwahati	India	23000	Guwahati, India
8	JRD Tata Sports Complex	Jamshedpur	India	24000	Jamshedpur, India
9	Tilak Maidan Stadium	Vasco da Gama	India	5000	Vasco da Gama, India
10	Kalinga Stadium	Bhubaneswar	India	15000	Bhubaneswar, India
11	Nehru Stadium	Chennai	India	40000	Chennai, India
12	EMS Stadium	Kozhikode	India	75000	Kozhikode, India
13	Jawaharlal Nehru Stadium	New Delhi	India	60000	New Delhi, India
14	Cooperage Ground	Mumbai	India	10000	Mumbai, India
15	Ambedkar Stadium	New Delhi	India	20000	New Delhi, India
\.


--
-- Data for Name: standings; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.standings (standing_id, league_id, team_id, "position", played_games, won, draw, lost, points, goals_for, goals_against, goal_difference, form) FROM stdin;
\.


--
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.teams (team_id, name, founded_year, league_id, stadium_id, coach_id, logo_url) FROM stdin;
1	Mohun Bagan Super Giant	1889	1	2	1	/static/images/teams/mohun_bagan.png
2	Odisha FC	2019	1	10	2	/static/images/teams/odisha_fc.png
3	Bengaluru FC	2013	1	3	3	/static/images/teams/benglaru_fc.png
4	Kerala Blasters FC	2014	1	1	4	/static/images/teams/kerla_blasters.png
5	Mumbai City FC	2014	1	4	5	/static/images/teams/mumbai_city.png
6	Hyderabad FC	2019	1	6	6	/static/images/teams/heydrabad_fc.png
7	FC Goa	2014	1	5	7	/static/images/teams/fc_goa.png
8	NorthEast United FC	2014	1	7	8	/static/images/teams/northeastunited_fc.png
9	East Bengal FC	1920	1	2	9	/static/images/teams/eastbengal_fc.png
10	Jamshedpur FC	2017	1	8	10	/static/images/teams/jamshedpur_fc.png
11	Chennaiyin FC	2014	1	11	11	/static/images/teams/chennaiyin_fc.png
12	Punjab FC	2005	1	13	12	/static/images/teams/punjab_fc.png
13	Gokulam Kerala FC	2017	2	12	13	/static/images/teams/GokulamKerala_FC.png
14	Churchill Brothers FC Goa	1988	2	5	14	/static/images/teams/Churchill_Brothers.png
15	TRAU FC	1972	2	7	15	/static/images/teams/TRAU_FC_logo.png
\.


--
--

2	Jolls Dmello	$2b$12$tY4ljgCwOBr4Weq7xXRJIerQn9gtEA2n33phaReIHKI.577M2gPYe	testuser1@example.com	f
1	lalu	$2b$12$1ONWnxBdquoXnEtfL7aE8OhqzGGFjzg7in2XsqRPWQw4tcMqz5/2i	testuser2@example.com	f
2	Jolls Dmello	$2b$12$tY4ljgCwOBr4Weq7xXRJIerQn9gtEA2n33phaReIHKI.577M2gPYe	Jollsdmello804@gmail.com	f
\.


--
-- Name: coaches_coach_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.coaches_coach_id_seq', 1, false);


--
-- Name: goals_goal_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.goals_goal_id_seq', 1, false);


--
-- Name: goals_goal_id_seq1; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.goals_goal_id_seq1', 1, false);


--
-- Name: matches_match_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.matches_match_id_seq', 1, false);


--
-- Name: matches_match_id_seq1; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.matches_match_id_seq1', 1, false);


--
-- Name: players_player_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.players_player_id_seq', 1, false);


--
-- Name: playoff_configs_config_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.playoff_configs_config_id_seq', 4, true);


--
-- Name: playoff_matches_playoff_match_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.playoff_matches_playoff_match_id_seq', 1, false);


--
-- Name: scorers_scorer_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.scorers_scorer_id_seq', 1, false);


--
-- Name: scores_score_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.scores_score_id_seq', 1, false);


--
-- Name: teams_team_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.teams_team_id_seq', 1, false);


--
-- Name: users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.users_user_id_seq', 2, true);


--
-- Name: coaches coaches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coaches
    ADD CONSTRAINT coaches_pkey PRIMARY KEY (coach_id);


--
-- Name: countries countries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.countries
    ADD CONSTRAINT countries_pkey PRIMARY KEY (country_id);


--
-- Name: goals goals_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goals
    ADD CONSTRAINT goals_pkey PRIMARY KEY (goal_id);


--
-- Name: leagues leagues_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leagues
    ADD CONSTRAINT leagues_pkey PRIMARY KEY (league_id);


--
-- Name: matches matches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_pkey PRIMARY KEY (match_id);


--
-- Name: password_resets password_resets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_pkey PRIMARY KEY (user_id);


--
-- Name: password_resets password_resets_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_token_key UNIQUE (token);


--
-- Name: players players_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_pkey PRIMARY KEY (player_id);


--
-- Name: playoff_configs playoff_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.playoff_configs
    ADD CONSTRAINT playoff_configs_pkey PRIMARY KEY (config_id);


--
-- Name: playoff_matches playoff_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.playoff_matches
    ADD CONSTRAINT playoff_matches_pkey PRIMARY KEY (playoff_match_id);


--
-- Name: referees referees_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.referees
    ADD CONSTRAINT referees_pkey PRIMARY KEY (referee_id);


--
-- Name: scorers scorers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scorers
    ADD CONSTRAINT scorers_pkey PRIMARY KEY (scorer_id);


--
-- Name: scores scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_pkey PRIMARY KEY (score_id);


--
-- Name: seasons seasons_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seasons
    ADD CONSTRAINT seasons_pkey PRIMARY KEY (season_id);


--
-- Name: stadiums stadiums_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stadiums
    ADD CONSTRAINT stadiums_pkey PRIMARY KEY (stadium_id);


--
-- Name: standings standings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.standings
    ADD CONSTRAINT standings_pkey PRIMARY KEY (standing_id);


--
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (team_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: goals goals_insert_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER goals_insert_trigger AFTER INSERT ON public.goals FOR EACH ROW EXECUTE FUNCTION public.update_scorers_from_goals();


--
-- Name: coaches coaches_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.coaches
    ADD CONSTRAINT coaches_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(team_id) ON DELETE SET NULL;


--
-- Name: goals goals_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goals
    ADD CONSTRAINT goals_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.matches(match_id) ON DELETE CASCADE;


--
-- Name: goals goals_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goals
    ADD CONSTRAINT goals_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.players(player_id) ON DELETE CASCADE;


--
-- Name: goals goals_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.goals
    ADD CONSTRAINT goals_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(team_id) ON DELETE CASCADE;


--
-- Name: match_referees match_referees_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_referees
    ADD CONSTRAINT match_referees_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.matches(match_id) ON DELETE CASCADE;


--
-- Name: match_referees match_referees_referee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.match_referees
    ADD CONSTRAINT match_referees_referee_id_fkey FOREIGN KEY (referee_id) REFERENCES public.referees(referee_id) ON DELETE CASCADE;


--
-- Name: matches matches_away_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES public.teams(team_id) ON DELETE CASCADE;


--
-- Name: matches matches_home_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES public.teams(team_id) ON DELETE CASCADE;


--
-- Name: matches matches_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(league_id) ON DELETE CASCADE;


--
-- Name: matches matches_season_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_season_id_fkey FOREIGN KEY (season_id) REFERENCES public.seasons(season_id) ON DELETE CASCADE;


--
-- Name: matches matches_stadium_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.matches
    ADD CONSTRAINT matches_stadium_id_fkey FOREIGN KEY (stadium_id) REFERENCES public.stadiums(stadium_id) ON DELETE SET NULL;


--
-- Name: password_resets password_resets_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(user_id) ON DELETE CASCADE;


--
-- Name: players players_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(team_id) ON DELETE SET NULL;


--
-- Name: playoff_matches playoff_matches_config_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.playoff_matches
    ADD CONSTRAINT playoff_matches_config_id_fkey FOREIGN KEY (config_id) REFERENCES public.playoff_configs(config_id);


--
-- Name: scorers scorers_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scorers
    ADD CONSTRAINT scorers_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(league_id) ON DELETE CASCADE;


--
-- Name: scorers scorers_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scorers
    ADD CONSTRAINT scorers_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.players(player_id) ON DELETE CASCADE;


--
-- Name: scorers scorers_season_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scorers
    ADD CONSTRAINT scorers_season_id_fkey FOREIGN KEY (season_id) REFERENCES public.seasons(season_id) ON DELETE CASCADE;


--
-- Name: scores scores_away_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_away_team_id_fkey FOREIGN KEY (away_team_id) REFERENCES public.teams(team_id) ON DELETE CASCADE;


--
-- Name: scores scores_home_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_home_team_id_fkey FOREIGN KEY (home_team_id) REFERENCES public.teams(team_id) ON DELETE CASCADE;


--
-- Name: scores scores_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_match_id_fkey FOREIGN KEY (match_id) REFERENCES public.matches(match_id) ON DELETE CASCADE;


--
-- Name: seasons seasons_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seasons
    ADD CONSTRAINT seasons_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(league_id) ON DELETE CASCADE;


--
-- Name: standings standings_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.standings
    ADD CONSTRAINT standings_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(league_id) ON DELETE CASCADE;


--
-- Name: standings standings_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.standings
    ADD CONSTRAINT standings_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(team_id) ON DELETE CASCADE;


--
-- Name: teams teams_league_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_league_id_fkey FOREIGN KEY (league_id) REFERENCES public.leagues(league_id) ON DELETE SET NULL;


--
-- Name: teams teams_stadium_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_stadium_id_fkey FOREIGN KEY (stadium_id) REFERENCES public.stadiums(stadium_id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

