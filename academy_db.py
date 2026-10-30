# academy_db.py â€” IT Expert Academy data layer
import sqlite3
from datetime import datetime
from database import get_connection

def init_academy():
    """Create Academy tables and seed initial content (idempotent)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lesson_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        passing_score INTEGER DEFAULT 70,
        max_attempts INTEGER DEFAULT 3,
        status TEXT DEFAULT 'published',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assessment_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER NOT NULL,
        question_type TEXT NOT NULL,
        question_text TEXT NOT NULL,
        options_json TEXT,
        correct_answer TEXT NOT NULL,
        explanation TEXT,
        points INTEGER DEFAULT 10,
        sequence_number INTEGER DEFAULT 1,
        FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assessment_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        attempt_number INTEGER DEFAULT 1,
        score INTEGER DEFAULT 0,
        max_score INTEGER DEFAULT 0,
        passed INTEGER DEFAULT 0,
        submitted_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (assessment_id) REFERENCES assessments(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assessment_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        selected_answer TEXT,
        is_correct INTEGER DEFAULT 0,
        points_awarded INTEGER DEFAULT 0,
        FOREIGN KEY (attempt_id) REFERENCES assessment_attempts(id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES assessment_questions(id) ON DELETE CASCADE
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS learning_paths (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        icon TEXT,
        color TEXT,
        target_level TEXT,
        sequence_number INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS academy_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learning_path_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        difficulty_level TEXT,
        language TEXT DEFAULT 'sw',
        estimated_duration_min INTEGER DEFAULT 0,
        status TEXT DEFAULT 'published',
        version INTEGER DEFAULT 1,
        created_by INTEGER,
        published_at TEXT DEFAULT (datetime('now','localtime')),
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (learning_path_id) REFERENCES learning_paths(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS course_modules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        sequence_number INTEGER DEFAULT 1,
        FOREIGN KEY (course_id) REFERENCES academy_courses(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        content TEXT,
        lesson_type TEXT DEFAULT 'text',
        sequence_number INTEGER DEFAULT 1,
        estimated_duration_min INTEGER DEFAULT 15,
        status TEXT DEFAULT 'published',
        FOREIGN KEY (module_id) REFERENCES course_modules(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS course_enrolments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        enrolled_at TEXT DEFAULT (datetime('now','localtime')),
        last_accessed_at TEXT,
        completed_at TEXT,
        UNIQUE(user_id, course_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS lesson_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        lesson_id INTEGER NOT NULL,
        status TEXT DEFAULT 'in_progress',
        started_at TEXT DEFAULT (datetime('now','localtime')),
        completed_at TEXT,
        UNIQUE(user_id, lesson_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS academy_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        activity_type TEXT NOT NULL,
        related_id INTEGER,
        recorded_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    _seed_python_quiz(cur)
    conn.commit()
    _seed_paths(cur)
    _seed_python_course(cur)
    _seed_course_placeholders(cur)
    conn.commit()
    conn.close()
def _seed_paths(cur):
    """Seed/update 5 categories. Slugs stay stable to preserve FKs."""
    categories = [
        # (slug, title, icon, color, description, seq)
        ("computer-foundations", "Computer & Digital Skills",
         "💻", "#2563EB",
         "Anza kujenga ujuzi wa msingi wa kompyuta — kutoka kwa kuwasha hadi kutumia ofisi.",
         1),
        ("programming-foundations", "Software & Programming",
         "⌨️", "#7C3AED",
         "Jifunze programu, uendelezaji wa tovuti, APIs, na databases.",
         2),
        ("ai-assisted-development", "AI & Data",
         "🤖", "#F47721",
         "AI, data analytics, machine learning, na AI-powered development.",
         3),
        ("web-development", "Networking, Security & Infrastructure",
         "🔒", "#0E8F78",
         "Networking, cybersecurity, Linux, na cloud infrastructure.",
         4),
        ("databases-backend", "Digital Business & Creative Technology",
         "🎨", "#DC2626",
         "Digital marketing, graphic design, na IT project management.",
         5),
    ]

    for slug, title, icon, color, desc, seq in categories:
        cur.execute(
            "UPDATE learning_paths SET title=?, icon=?, color=?, "
            "description=?, sequence_number=? WHERE slug=?",
            (title, icon, color, desc, seq, slug))
        cur.execute(
            "INSERT OR IGNORE INTO learning_paths "
            "(title, slug, description, icon, color, target_level, sequence_number) "
            "VALUES (?, ?, ?, ?, ?, 'Beginner', ?)",
            (title, slug, desc, icon, color, seq))
def _seed_python_course(cur):
    """Seed one complete course: Python Fundamentals 101."""
    existing = cur.execute(
        "SELECT id FROM academy_courses WHERE slug = 'python-fundamentals-101'"
    ).fetchone()
    if existing:
        return

    path = cur.execute(
        "SELECT id FROM learning_paths WHERE slug = 'programming-foundations'"
    ).fetchone()
    if not path:
        return

    cur.execute(
        "INSERT INTO academy_courses (learning_path_id, title, slug, description, "
        "difficulty_level, language, estimated_duration_min, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'published')",
        (path["id"], "Python Fundamentals 101", "python-fundamentals-101",
         "Kozi ya kuanzia Python â€” kuanzia dhana za msingi hadi kuandika programu yako ya kwanza yenye mantiki.",
         "Beginner", "sw", 240))

    course_id = cur.lastrowid

    modules = [
        ("Getting Started with Python",
         "Tambua Python, jinsi ya kuandika msimbo, na kukimbiza programu yako ya kwanza."),
        ("Variables and Data",
         "Hifadhi taarifa kwa variables na ujue aina za data katika Python."),
        ("Making Decisions",
         "Tumia masharti (if/else) kufanya programu yako ifanye maamuzi."),
    ]

    lessons_data = {
        0: [
            ("What is Python?",
             "<h2>What is Python?</h2><p>Python ni lugha ya programu inayojulikana kwa urahisi wake. Ilianzishwa mwaka 1991 na Guido van Rossum na leo inatumika katika:</p><ul><li>Uendelezaji wa tovuti (web development)</li><li>Sayansi ya data (data science)</li><li>Akili bandia (artificial intelligence)</li><li>Uendeshaji wa mifumo (automation)</li></ul><h3>Kwa nini Python?</h3><p>Python ni rahisi kusoma â€” karibu kama Kiingereza cha kawaida. Hii inafanya iwe lugha nzuri kwa wanaoanza.</p><pre><code>print(\"Habari, Dunia!\")</code></pre><p>Mstari huu mmoja unaandika ujumbe kwenye skrini. Ni programu yako ya kwanza!</p><h3>Unachohitaji kuanza</h3><ul><li>Kompyuta (Windows, Mac, au Linux)</li><li>Python iliyosakinishwa (tutaiona kwenye somo lijalo)</li><li>Hamasa ya kujifunza</li></ul>", 15),
            ("Your First Program",
             "<h2>Your First Program</h2><p>Tutaandika programu yetu ya kwanza halisi. Fungua Python (au editor yoyote) na andika:</p><pre><code>print(\"Karibu IT Expert Academy!\")</code></pre><h3>Kile kinachotokea</h3><ol><li><strong>print</strong> â€” ni kazi (function) inayochapisha kitu kwenye skrini</li><li><strong>\"Karibu...\"</strong> â€” ni maandishi (string) tuliyotaka kuchapisha</li><li><strong>(...)</strong> â€” mabano yanaelekeza print kile cha kuchapisha</li></ol><h3>Jaribu</h3><p>Badilisha maandishi ndani ya quotes na uone kinachotokea:</p><pre><code>print(\"Jina langu ni [jina lako]\")</code></pre><p>Hongera! Umeandika programu yako ya kwanza yenye maana.</p>", 20),
            ("Variables and Data Types",
             "<h2>Variables and Data Types</h2><p><strong>Variable</strong> ni chombo cha kuhifadhi taarifa. Fikiria kama sanduku lenye jina:</p><pre><code>jina = \"Amina\"\numri = 25\nurefu = 1.68\namefaulu = True</code></pre><h3>Aina za data kuu</h3><ul><li><strong>String (str)</strong> â€” maandishi: <code>\"Habari\"</code></li><li><strong>Integer (int)</strong> â€” namba nzima: <code>42</code></li><li><strong>Float</strong> â€” namba yenye desimali: <code>3.14</code></li><li><strong>Boolean (bool)</strong> â€” kweli au uongo: <code>True</code> / <code>False</code></li></ul><h3>Kuchapisha variables</h3><pre><code>jina = \"Amina\"\nprint(\"Habari, \" + jina)</code></pre><p>Matokeo: <em>Habari, Amina</em></p><h3>Kumbuka</h3><p>Majina ya variables hayawezi kuwa na nafasi au kuanza na namba. Tumia <code>_</code> badala ya nafasi: <code>jina_langu</code>.</p>", 25),
                     # LESSON 4
        {
            "title": "Semantic HTML: Structure That Means Something",
            "duration": 25,
            "objectives": [
                "Elewa tofauti kati ya <div> na semantic elements",
                "Tumia <header>, <nav>, <main>, <section>, <article>, <aside>, <footer>",
                "Jenga ukurasa wenye muundo unaosomeka na screen readers",
                "Jua kwa nini semantic HTML ni muhimu kwa SEO",
            ],
            "sections": [
                {"type": "text", "title": "Semantic HTML ni nini?",
                 "body": "Semantic HTML ni kutumia tags zinazoeleza MAANA ya maudhui, si muonekano tu. <div> haisemi kitu — ni chombo tupu. <nav> inasema 'hii ni sehemu ya viungo vya urambazaji'. Hii inasaidia: (1) screen readers kwa watu wasioona, (2) Google kuelewa ukurasa wako, (3) wewe mwenyewe kusoma code yako baadaye."},
                {"type": "callout", "title": "Fikiria kama gazeti",
                 "body": "Gazeti lina kichwa (header), sehemu kuu (main), makala kadhaa (article), pembeni matangazo (aside), na chini taarifa za kampuni (footer). HTML semantics ni hivyo hivyo kwa ukurasa wa wavuti."},
                {"type": "code", "title": "Muundo wa semantic page",
                 "language": "html",
                 "body": "Huu ni 'skeleton' ya ukurasa wa kisasa:",
                 "code": "<!DOCTYPE html>\n<html lang=\"sw\">\n<head>\n  <meta charset=\"UTF-8\">\n  <title>Blog Yangu</title>\n</head>\n<body>\n  <header>\n    <h1>Blog Yangu</h1>\n    <nav>\n      <a href=\"/\">Nyumbani</a>\n      <a href=\"/about\">Kuhusu</a>\n    </nav>\n  </header>\n\n  <main>\n    <article>\n      <h2>Makala ya Kwanza</h2>\n      <p>Maudhui ya makala...</p>\n    </article>\n  </main>\n\n  <aside>\n    <h3>Makala Zinazohusiana</h3>\n    <ul>\n      <li><a href=\"/post2\">Makala 2</a></li>\n    </ul>\n  </aside>\n\n  <footer>\n    <p>&copy; 2026 Blog Yangu</p>\n  </footer>\n</body>\n</html>"},
                {"type": "text", "title": "Kila tag na kazi yake",
                 "body": "<header> = kichwa cha ukurasa au sehemu. <nav> = viungo vya urambazaji. <main> = maudhui makuu (MOJA kwa kila ukurasa). <section> = sehemu yenye kichwa chake. <article> = maudhui yanayojitegemea (blog post, habari). <aside> = maudhui ya pembeni (matangazo, viungo). <footer> = sehemu ya chini (copyright, mawasiliano)."},
                {"type": "callout", "title": "Kanuni moja",
                 "body": "<main> ni MOJA tu kwa kila ukurasa. <header>, <nav>, <footer> zinaweza kuwa nyingi (mfano: kila <article> inaweza kuwa na <header> yake)."},
            ],
            "key_takeaways": [
                "Semantic HTML inaeleza maana, si muonekano",
                "<div> ni neutral; tumia pale hakuna semantic element inayofaa",
                "<main> ni moja kwa kila ukurasa — maudhui makuu",
                "<article> = inajitegemea; <section> = sehemu yenye kichwa",
                "Semantic HTML = accessibility + SEO + maintainability",
            ],
            "common_mistakes": [
                {"mistake": "Kutumia <div> kwa kila kitu",
                 "fix": "Kama kuna semantic element inayofaa (nav, main, article), tumia hiyo kwanza."},
                {"mistake": "Kutumia <main> zaidi ya moja",
                 "fix": "<main> ni moja tu — sehemu kuu ya maudhui. Sehemu nyingine ni <section> au <article>."},
                {"mistake": "Kuweka <nav> kwenye footer kwa viungo vya kawaida",
                 "fix": "<nav> ni kwa viungo VYA URAMBAZIJI. Viungo vya kawaida (kama copyright) havihitaji <nav>."},
            ],
            "exercise_prompt": "Chukua ukurasa wako wa wasifu ('my-bio.html' kutoka somo la 2) na uubadilishe kutumia semantic HTML: <header> yenye <h1> na <nav>, <main> yenye <section> na <h2>, na <footer> yenye copyright.",
            "exercise_solution": "<!DOCTYPE html>\n<html lang=\"sw\">\n<head>\n  <meta charset=\"UTF-8\">\n  <title>Wasifu Wangu</title>\n</head>\n<body>\n  <header>\n    <h1>Amina Hassan</h1>\n    <nav>\n      <a href=\"#about\">Kuhusu</a>\n      <a href=\"#hobbies\">Mambo Ninayopenda</a>\n    </nav>\n  </header>\n\n  <main>\n    <section id=\"about\">\n      <h2>Kuhusu Mimi</h2>\n      <p>Mimi ni mwanafunzi wa IT Level 4.</p>\n    </section>\n\n    <section id=\"hobbies\">\n      <h2>Mambo Ninayopenda</h2>\n      <ul>\n        <li>Programu</li>\n        <li>Muziki</li>\n        <li>Kusoma</li>\n      </ul>\n    </section>\n  </main>\n\n  <footer>\n    <p>&copy; 2026 Amina Hassan</p>\n  </footer>\n</body>\n</html>",
        },

        # LESSON 5
        {
            "title": "Forms Part 1: Inputs and Labels",
            "duration": 30,
            "objectives": [
                "Unda fomu yenye <input> za aina mbalimbali",
                "Tumia <label> kuunganisha maandishi na input (accessibility)",
                "Jua input types 8 muhimu za HTML5",
                "Tumia required, placeholder, minlength kwa validation",
            ],
            "sections": [
                {"type": "text", "title": "Forms ni nini?",
                 "body": "Fomu (form) inakusanya taarifa kutoka kwa mtumiaji: jina, email, nenosiri, maoni. Kila kitu kwenye fomu kinaingia kwenye <form>...</form>. Bila form, hakuna login, hakuna usajili, hakuna malipo — hakuna tovuti inayofanya kazi."},
                {"type": "callout", "title": "Kanuni #1 ya fomu",
                 "body": "KILA input LAZIMA iwe na <label>. Bila label, watu wasioona hawawezi kujua input ni ya nini, na kubonyeza maandishi ya label hakuweki focus kwenye input."},
                {"type": "text", "title": "Input types 8 muhimu",
                 "body": "HTML5 ina input types 20+. Hizi 8 zinatosha kwa 95% ya fomu: text (maandishi ya kawaida), email (barua pepe — ina validate automatically), password (maandishi yaliyofichwa), number (namba), tel (simu), date (tarehe), checkbox (chagua nyingi), radio (chagua moja)."},
                {"type": "code", "title": "Fomu kamili ya usajili",
                 "language": "html",
                 "body": "",
                 "code": "<form action=\"/signup\" method=\"POST\">\n  <div>\n    <label for=\"full_name\">Jina Kamili</label>\n    <input type=\"text\" id=\"full_name\" name=\"full_name\"\n           required minlength=\"3\" placeholder=\"Mf. Amina Hassan\">\n  </div>\n\n  <div>\n    <label for=\"email\">Barua Pepe</label>\n    <input type=\"email\" id=\"email\" name=\"email\"\n           required placeholder=\"amina@example.com\">\n  </div>\n\n  <div>\n    <label for=\"password\">Nenosiri</label>\n    <input type=\"password\" id=\"password\" name=\"password\"\n           required minlength=\"8\">\n  </div>\n\n  <div>\n    <label for=\"age\">Umri</label>\n    <input type=\"number\" id=\"age\" name=\"age\" min=\"13\" max=\"120\">\n  </div>\n\n  <button type=\"submit\">Sajili</button>\n</form>"},
                {"type": "text", "title": "for + id — ufunguo wa label",
                 "body": "<label for=\"full_name\"> na <input id=\"full_name\"> vinahusiana kwa 'for' = 'id'. Bonyeza maandishi 'Jina Kamili' — focus inaruka kwenye input. Hii ni accessibility ya msingi."},
                {"type": "text", "title": "Attributes muhimu",
                 "body": "required = lazima ijazwe. minlength/maxlength = urefu wa chini/juu. min/max = thamani ya chini/juu (kwa namba). placeholder = maelezo ya mfano (yanaonekana tupu). name = jina la field kwenye form submission (muhimu kwa server)."},
                {"type": "callout", "title": "Mstari mmoja",
                 "body": "Kila input inahitaji: (1) type, (2) id, (3) name, (4) label inayohusiana. Vingine ni bonus."},
            ],
            "key_takeaways": [
                "<form> inakusanya taarifa za mtumiaji",
                "KILA input ina <label for='...'> inayohusiana na id",
                "type='email' ina validate automatically",
                "required inazuia submission mpaka ijazwe",
                "name attribute ni muhimu kwa server kupokea data",
            ],
            "common_mistakes": [
                {"mistake": "Kutumia placeholder badala ya label",
                 "fix": "Placeholder inatoweka unapoandika. Label daima inaonekana. Tumia zote mbili."},
                {"mistake": "Kusahau name attribute kwenye input",
                 "fix": "Bila name, server HAITAPOKEA thamani. Kila input inahitaji name."},
                {"mistake": "Kutumia type='text' kwa nenosiri",
                 "fix": "Tumia type='password' — inaficha maandishi na kuzuia kuibiwa kwa kuangalia."},
                {"mistake": "id na for hazifanani",
                 "fix": "<label for='x'> LAZIMA ilingane na <input id='x'>."},
            ],
            "exercise_prompt": "Unda fomu ya 'wasiliana nasi' yenye: jina (text), email, simu (tel), ujumbe mfupi (textarea — tutajifunza somo lijalo, kwa sasa tumia input text), na button ya 'Tuma'.",
            "exercise_solution": "<form action=\"/contact\" method=\"POST\">\n  <div>\n    <label for=\"name\">Jina Lako</label>\n    <input type=\"text\" id=\"name\" name=\"name\" required>\n  </div>\n  <div>\n    <label for=\"email\">Barua Pepe</label>\n    <input type=\"email\" id=\"email\" name=\"email\" required>\n  </div>\n  <div>\n    <label for=\"phone\">Namba ya Simu</label>\n    <input type=\"tel\" id=\"phone\" name=\"phone\" placeholder=\"0712 345 678\">\n  </div>\n  <div>\n    <label for=\"message\">Ujumbe</label>\n    <input type=\"text\" id=\"message\" name=\"message\" required>\n  </div>\n  <button type=\"submit\">Tuma →</button>\n</form>",
        },

        # LESSON 6
        {
            "title": "Forms Part 2: Select, Textarea, and Validation",
            "duration": 30,
            "objectives": [
                "Tumia <textarea> kwa maandishi marefu",
                "Tumia <select> kwa dropdown",
                "Tumia checkbox (chagua nyingi) na radio (chagua moja)",
                "Jua jinsi HTML5 inavyofanya validation papo hapo",
            ],
            "sections": [
                {"type": "text", "title": "Textarea — maandishi marefu",
                 "body": "Input ya kawaida ni mstari mmoja. <textarea> ni kwa paragraph, maelezo, comments. Ina rows (urefu wa mstari) na cols (upana)." },
                {"type": "code", "title": "Textarea",
                 "language": "html",
                 "body": "",
                 "code": "<label for=\"feedback\">Maoni yako</label>\n<textarea id=\"feedback\" name=\"feedback\" rows=\"5\"\n          maxlength=\"500\" placeholder=\"Andika maoni hapa (herufi 500 max)\"></textarea>"},
                {"type": "text", "title": "Select — dropdown",
                 "body": "<select> inaunda dropdown. Kila chaguo ni <option>. value ni kile kinachotumwa kwa server; maandishi kati ya <option> ni kile mtumiaji anaona."},
                {"type": "code", "title": "Select dropdown",
                 "language": "html",
                 "body": "",
                 "code": "<label for=\"course\">Chagua Kozi</label>\n<select id=\"course\" name=\"course\" required>\n  <option value=\"\">— Chagua —</option>\n  <option value=\"html\">HTML5</option>\n  <option value=\"css\">CSS3</option>\n  <option value=\"js\">JavaScript</option>\n</select>"},
                {"type": "text", "title": "Checkbox — chagua nyingi",
                 "body": "Checkbox inaruhusu mtumiaji kuchagua zaidi ya moja. Kila checkbox ni input TOFAUTI (ina name na id yake)." },
                {"type": "code", "title": "Checkbox group",
                 "language": "html",
                 "body": "",
                 "code": "<fieldset>\n  <legend>Mambo Unayopenda</legend>\n\n  <input type=\"checkbox\" id=\"music\" name=\"hobby\" value=\"music\">\n  <label for=\"music\">Muziki</label><br>\n\n  <input type=\"checkbox\" id=\"sports\" name=\"hobby\" value=\"sports\">\n  <label for=\"sports\">Michezo</label><br>\n\n  <input type=\"checkbox\" id=\"reading\" name=\"hobby\" value=\"reading\">\n  <label for=\"reading\">Kusoma</label>\n</fieldset>"},
                {"type": "text", "title": "Radio — chagua MOJA tu",
                 "body": "Radio ni kama checkbox lakini unachagua MOJA tu. Kila radio inayohusiana LAZIMA iwe na name ILE ILE — hii ndiyo inayowafanya wawe kikundi."},
                {"type": "code", "title": "Radio group",
                 "language": "html",
                 "body": "",
                 "code": "<fieldset>\n  <legend>Jinsia</legend>\n\n  <input type=\"radio\" id=\"male\" name=\"gender\" value=\"male\">\n  <label for=\"male\">Me</label><br>\n\n  <input type=\"radio\" id=\"female\" name=\"gender\" value=\"female\">\n  <label for=\"female\">Ke</label>\n</fieldset>"},
                {"type": "callout", "title": "Validation ya HTML5 — bure!",
                 "body": "Ukiweka required, minlength, maxlength, type='email', pattern — browser inafanya validation AUTOMATICALLY. Mtumiaji hawezi ku-submit fomu yenye kosa. Hii si badala ya server validation (lazima uwe na server-side pia), lakini inaboresha UX sana."},
                {"type": "code", "title": "Mfano wa validation",
                 "language": "html",
                 "body": "Fomu hii haitakubali submission kama: jina ni fupi, email si sahihi, au nenosiri halina herufi 8.",
                 "code": "<form>\n  <label for=\"u\">Jina (angalau 3)</label>\n  <input type=\"text\" id=\"u\" required minlength=\"3\">\n\n  <label for=\"e\">Email</label>\n  <input type=\"email\" id=\"e\" required>\n\n  <label for=\"p\">Nenosiri (8+)</label>\n  <input type=\"password\" id=\"p\" required minlength=\"8\">\n\n  <button type=\"submit\">Tuma</button>\n</form>"},
            ],
            "key_takeaways": [
                "<textarea> kwa maandishi marefu (paragraph, comments)",
                "<select> + <option> kwa dropdown",
                "Checkbox = chagua nyingi; Radio = chagua moja (name ile ile)",
                "HTML5 inafanya validation papo hapo: required, minlength, type='email'",
                "LAZIMA uwe na server-side validation pia — HTML5 si kinga kamili",
            ],
            "common_mistakes": [
                {"mistake": "Radio zenye name tofauti",
                 "fix": "Zote za kikundi kimoja LAZIMA ziwe na name ILE ILE."},
                {"mistake": "Kutumia <input> kwa maandishi marefu",
                 "fix": "Tumia <textarea rows='5'> kwa paragraph, maelezo."},
                {"mistake": "Kutegemea HTML5 validation pekee",
                 "fix": "HTML5 inaweza kuzimwa. Server LAZIMA ifanye validation upya."},
                {"mistake": "Kusahau <legend> ndani ya <fieldset>",
                 "fix": "<fieldset> bila <legend> haisemi kikundi ni cha nini. Ongeza <legend>."},
            ],
            "exercise_prompt": "Unda fomu kamili ya 'maoni ya kozi' yenye: jina (text, required), email (email, required), kozi (select: HTML, CSS, JS), kiwango (radio: Beginner, Intermediate, Advanced), mada zinazokuvutia (checkbox 3: design, programming, security), maoni (textarea, maxlength 500), na button 'Tuma Maoni'.",
            "exercise_solution": "<form action=\"/feedback\" method=\"POST\">\n  <label for=\"name\">Jina</label>\n  <input type=\"text\" id=\"name\" name=\"name\" required>\n\n  <label for=\"email\">Email</label>\n  <input type=\"email\" id=\"email\" name=\"email\" required>\n\n  <label for=\"course\">Kozi</label>\n  <select id=\"course\" name=\"course\" required>\n    <option value=\"\">— Chagua —</option>\n    <option value=\"html\">HTML</option>\n    <option value=\"css\">CSS</option>\n    <option value=\"js\">JavaScript</option>\n  </select>\n\n  <fieldset>\n    <legend>Kiwango</legend>\n    <input type=\"radio\" id=\"b\" name=\"level\" value=\"beginner\">\n    <label for=\"b\">Beginner</label>\n    <input type=\"radio\" id=\"i\" name=\"level\" value=\"intermediate\">\n    <label for=\"i\">Intermediate</label>\n    <input type=\"radio\" id=\"a\" name=\"level\" value=\"advanced\">\n    <label for=\"a\">Advanced</label>\n  </fieldset>\n\n  <fieldset>\n    <legend>Mada</legend>\n    <input type=\"checkbox\" id=\"d\" name=\"topic\" value=\"design\">\n    <label for=\"d\">Design</label>\n    <input type=\"checkbox\" id=\"p\" name=\"topic\" value=\"programming\">\n    <label for=\"p\">Programming</label>\n    <input type=\"checkbox\" id=\"s\" name=\"topic\" value=\"security\">\n    <label for=\"s\">Security</label>\n  </fieldset>\n\n  <label for=\"msg\">Maoni</label>\n  <textarea id=\"msg\" name=\"message\" rows=\"5\" maxlength=\"500\"></textarea>\n\n  <button type=\"submit\">Tuma Maoni →</button>\n</form>",
        },
        ],
        1: [
            ("if / elif / else",
             "<h2>if / elif / else â€” Kufanya Maamuzi</h2><p>Programu mara nyingi zinahitaji kuchagua kile cha kufanya kulingana na hali. Tunatumia <code>if</code>:</p><pre><code>umri = 18\nif umri >= 18:\n    print(\"Wewe ni mtu mzima\")\nelse:\n    print(\"Wewe ni kijana\")</code></pre><h3>elif kwa hali nyingi</h3><pre><code>alama = 75\nif alama >= 80:\n    print(\"A\")\nelif alama >= 60:\n    print(\"B\")\nelse:\n    print(\"F\")</code></pre><h3>Kumbuka</h3><ul><li><code>if</code> na <code>else</code> zinahitaji <code>:</code> mwishoni</li><li>Msimbo ndani ya <code>if</code> unahitaji <strong>indentation</strong> (nafasi 4)</li><li>Masharti yanaweza kuwa <code>==</code>, <code>!=</code>, <code>&gt;</code>, <code>&lt;</code>, <code>&gt;=</code>, <code>&lt;=</code></li></ul>", 30),
        ],
    }

    for mi, (mtitle, mdesc) in enumerate(modules):
        cur.execute(
            "INSERT INTO course_modules (course_id, title, description, sequence_number) "
            "VALUES (?, ?, ?, ?)",
            (course_id, mtitle, mdesc, mi + 1))
        module_id = cur.lastrowid

        for li, item in enumerate(lessons_data.get(mi, [])):
            if isinstance(item, dict):
                ltitle = item.get('title', '')
                lcontent = item.get('content', '')
                lmin = item.get('duration', 15)
            else:
                ltitle = item[0] if len(item) > 0 else ''
                lcontent = item[1] if len(item) > 1 else ''
                lmin = item[2] if len(item) > 2 else 15
            cur.execute(
                "INSERT INTO lessons (module_id, title, content, sequence_number, estimated_duration_min) "
                "VALUES (?, ?, ?, ?, ?)",
                (module_id, ltitle, lcontent, li + 1, lmin))


# ============================================================
# READ FUNCTIONS
# ============================================================
def get_all_paths():
    conn = get_connection()
    rows = conn.execute(
        "SELECT p.*, "
        "(SELECT COUNT(*) FROM academy_courses c WHERE c.learning_path_id = p.id "
        " AND c.status = 'published') AS course_count "
        "FROM learning_paths p WHERE p.status = 'active' "
        "ORDER BY p.sequence_number, p.id").fetchall()
    conn.close()
    return rows


def get_path_by_slug(slug):
    conn = get_connection()
    row = conn.execute("SELECT * FROM learning_paths WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    return row


def get_all_courses():
    conn = get_connection()
    rows = conn.execute(
        "SELECT c.*, p.title AS path_title, p.icon AS path_icon, p.color AS path_color, "
        "p.sequence_number AS path_seq, "
        "(SELECT COUNT(*) FROM course_modules WHERE course_id = c.id) AS module_count, "
        "(SELECT COUNT(*) FROM lessons l JOIN course_modules m ON l.module_id = m.id "
        " WHERE m.course_id = c.id) AS lesson_count "
        "FROM academy_courses c JOIN learning_paths p ON c.learning_path_id = p.id "
        "WHERE c.status IN ('published', 'coming_soon') "
        "ORDER BY p.sequence_number, c.id").fetchall()
    conn.close()
    return rows

def get_course(course_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT c.*, p.title AS path_title, p.icon AS path_icon, p.color AS path_color "
        "FROM academy_courses c JOIN learning_paths p ON c.learning_path_id = p.id "
        "WHERE c.id = ?", (course_id,)).fetchone()
    conn.close()
    return row


def get_course_modules(course_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM course_modules WHERE course_id = ? "
        "ORDER BY sequence_number, id", (course_id,)).fetchall()
    conn.close()
    return rows


def get_lessons_for_module(module_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM lessons WHERE module_id = ? AND status = 'published' "
        "ORDER BY sequence_number, id", (module_id,)).fetchall()
    conn.close()
    return rows


def get_lesson(lesson_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT l.*, m.course_id, m.title AS module_title, "
        "c.title AS course_title, c.slug AS course_slug "
        "FROM lessons l JOIN course_modules m ON l.module_id = m.id "
        "JOIN academy_courses c ON m.course_id = c.id "
        "WHERE l.id = ?", (lesson_id,)).fetchone()
    conn.close()
    return row


# ============================================================
# ENROLMENT & PROGRESS
# ============================================================
def is_enrolled(user_id, course_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM course_enrolments WHERE user_id = ? AND course_id = ?",
        (user_id, course_id)).fetchone()
    conn.close()
    return row is not None


def enrol_user(user_id, course_id):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO course_enrolments (user_id, course_id) VALUES (?, ?)",
            (user_id, course_id))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_user_enrollments(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT e.*, c.title, c.slug, c.description, c.estimated_duration_min, "
        "p.title AS path_title, p.icon AS path_icon, p.color AS path_color, "
        "(SELECT COUNT(*) FROM lessons l JOIN course_modules m ON l.module_id = m.id "
        " WHERE m.course_id = c.id) AS total_lessons, "
        "(SELECT COUNT(*) FROM lesson_progress lp "
        " JOIN lessons l ON lp.lesson_id = l.id "
        " JOIN course_modules m ON l.module_id = m.id "
        " WHERE lp.user_id = ? AND m.course_id = c.id AND lp.status = 'completed') AS completed_lessons "
        "FROM course_enrolments e "
        "JOIN academy_courses c ON e.course_id = c.id "
        "JOIN learning_paths p ON c.learning_path_id = p.id "
        "WHERE e.user_id = ? ORDER BY e.last_accessed_at DESC, e.enrolled_at DESC",
        (user_id, user_id)).fetchall()
    conn.close()
    return rows


def get_lesson_progress(user_id, lesson_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM lesson_progress WHERE user_id = ? AND lesson_id = ?",
        (user_id, lesson_id)).fetchone()
    conn.close()
    return row


def mark_lesson_complete(user_id, lesson_id):
    conn = get_connection()
    conn.execute(
        "INSERT INTO lesson_progress (user_id, lesson_id, status, completed_at) "
        "VALUES (?, ?, 'completed', datetime('now','localtime')) "
        "ON CONFLICT(user_id, lesson_id) DO UPDATE SET "
        "status = 'completed', completed_at = datetime('now','localtime')",
        (user_id, lesson_id))
    # Touch enrolment
    lesson = get_lesson(lesson_id)
    if lesson:
        conn.execute(
            "UPDATE course_enrolments SET last_accessed_at = datetime('now','localtime') "
            "WHERE user_id = ? AND course_id = ?",
            (user_id, lesson["course_id"]))
    conn.commit()
    conn.close()


def touch_enrolment(user_id, course_id):
    conn = get_connection()
    conn.execute(
        "UPDATE course_enrolments SET last_accessed_at = datetime('now','localtime') "
        "WHERE user_id = ? AND course_id = ?", (user_id, course_id))
    conn.commit()
    conn.close()


def get_user_academy_stats(user_id):
    conn = get_connection()
    enrolled = conn.execute(
        "SELECT COUNT(*) FROM course_enrolments WHERE user_id = ?",
        (user_id,)).fetchone()[0]
    completed = conn.execute(
        "SELECT COUNT(*) FROM lesson_progress WHERE user_id = ? AND status = 'completed'",
        (user_id,)).fetchone()[0]
    courses_done = conn.execute(
        "SELECT COUNT(*) FROM course_enrolments WHERE user_id = ? AND status = 'completed'",
        (user_id,)).fetchone()[0]
    conn.close()
    return {"enrolled": enrolled, "lessons_completed": completed, "courses_completed": courses_done}


def get_continue_learning(user_id):
    """Get the most recent in-progress lesson for the user."""
    conn = get_connection()
    row = conn.execute(
        "SELECT l.id AS lesson_id, l.title AS lesson_title, c.id AS course_id, "
        "c.title AS course_title, c.slug AS course_slug "
        "FROM course_enrolments e "
        "JOIN academy_courses c ON e.course_id = c.id "
        "JOIN course_modules m ON m.course_id = c.id "
        "JOIN lessons l ON l.module_id = m.id "
        "WHERE e.user_id = ? "
        "AND l.id NOT IN (SELECT lesson_id FROM lesson_progress WHERE user_id = ? AND status = 'completed') "
        "AND e.last_accessed_at IS NOT NULL "
        "ORDER BY e.last_accessed_at DESC, m.sequence_number, l.sequence_number "
        "LIMIT 1", (user_id, user_id)).fetchone()
    conn.close()
    return row


def get_first_lesson(course_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT l.id FROM lessons l JOIN course_modules m ON l.module_id = m.id "
        "WHERE m.course_id = ? AND l.status = 'published' "
        "ORDER BY m.sequence_number, l.sequence_number LIMIT 1",
        (course_id,)).fetchone()
    conn.close()
    return row["id"] if row else None


def get_next_lesson(current_lesson_id):
    """Find the next lesson in the same course."""
    conn = get_connection()
    current = get_lesson(current_lesson_id)
    if not current:
        conn.close()
        return None
    row = conn.execute(
        "SELECT l.id FROM lessons l JOIN course_modules m ON l.module_id = m.id "
        "WHERE m.course_id = ? AND l.status = 'published' "
        "AND (m.sequence_number > (SELECT sequence_number FROM course_modules WHERE id = ?) "
        "  OR (m.sequence_number = (SELECT sequence_number FROM course_modules WHERE id = ?) "
        "      AND l.sequence_number > (SELECT sequence_number FROM lessons WHERE id = ?))) "
        "ORDER BY m.sequence_number, l.sequence_number LIMIT 1",
        (current["course_id"], current["module_id"], current["module_id"], current_lesson_id)).fetchone()
    conn.close()
    return row["id"] if row else None
def _seed_python_quiz(cur):
    """Seed one quiz for the Variables and Data Types lesson."""
    existing = cur.execute("SELECT id FROM assessments LIMIT 1").fetchone()
    if existing:
        return
    lesson = cur.execute(
        "SELECT id FROM lessons WHERE title = 'Variables and Data Types' LIMIT 1"
    ).fetchone()
    if not lesson:
        return

    import json as _json

    cur.execute(
        "INSERT INTO assessments (lesson_id, title, description, passing_score, max_attempts) "
        "VALUES (?, ?, ?, ?, ?)",
        (lesson["id"], "Variables & Data Types â€” Quiz",
         "Jaribu uelewa wako wa variables na aina za data katika Python.",
         70, 3))
    aid = cur.lastrowid

    questions = [
        ("multiple_choice", "Ni ipi kati ya hizi ni string?",
         ["42", '"Habari"', "3.14", "True"], "1",
         "String ni maandishi yaliyofungwa kwenye quotes. `\"Habari\"` ni string.", 10),
        ("true_false", '`jina = "Amina"` inahifadhi maandishi kwenye variable inayoitwa `jina`.',
         ["True", "False"], "0",
         "Kweli. Ishara `=` inahifadhi thamani upande wa kulia kwenye variable upande wa kushoto.", 10),
        ("multiple_choice", "Namba `3.14` ni aina gani ya data?",
         ["Integer", "String", "Float", "Boolean"], "2",
         "Float ni namba yenye desimali (pointi).", 10),
        ("true_false", "Variable inaweza kuanza na namba, mfano `1jina`.",
         ["True", "False"], "1",
         "Uongo. Variable haiwezi kuanza na namba. Tumia `jina1` badala yake.", 10),
        ("multiple_choice", "Kuchapisha variable `jina` kwenye Python, unatumia:",
         ["show jina", "print(jina)", "echo jina", "display jina"], "1",
         "`print(jina)` inachapisha thamani ya variable.", 10),
    ]

    for qi, (qtype, qtext, options, correct, explanation, pts) in enumerate(questions):
        cur.execute(
            "INSERT INTO assessment_questions "
            "(assessment_id, question_type, question_text, options_json, "
            "correct_answer, explanation, points, sequence_number) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (aid, qtype, qtext, _json.dumps(options, ensure_ascii=False),
             correct, explanation, pts, qi + 1))
# ============================================================
# QUIZZES / ASSESSMENTS
# ============================================================
def get_assessment_for_lesson(lesson_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM assessments WHERE lesson_id = ? AND status = 'published'",
        (lesson_id,)).fetchone()
    conn.close()
    return row


def get_assessment(assessment_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT a.*, l.title AS lesson_title, l.id AS lesson_id, "
        "m.course_id, c.title AS course_title "
        "FROM assessments a "
        "JOIN lessons l ON a.lesson_id = l.id "
        "JOIN course_modules m ON l.module_id = m.id "
        "JOIN academy_courses c ON m.course_id = c.id "
        "WHERE a.id = ?", (assessment_id,)).fetchone()
    conn.close()
    return row


def get_assessment_questions(assessment_id):
    import json as _json
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM assessment_questions WHERE assessment_id = ? "
        "ORDER BY sequence_number, id", (assessment_id,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d["options"] = _json.loads(d.get("options_json") or "[]")
        except Exception:
            d["options"] = []
        result.append(d)
    return result


def get_total_points(assessment_id):
    conn = get_connection()
    n = conn.execute(
        "SELECT COALESCE(SUM(points), 0) FROM assessment_questions WHERE assessment_id = ?",
        (assessment_id,)).fetchone()[0]
    conn.close()
    return n or 0


def get_user_attempts(assessment_id, user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM assessment_attempts WHERE assessment_id = ? AND user_id = ? "
        "ORDER BY attempt_number DESC", (assessment_id, user_id)).fetchall()
    conn.close()
    return rows


def get_best_attempt(assessment_id, user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM assessment_attempts WHERE assessment_id = ? AND user_id = ? "
        "ORDER BY score DESC, submitted_at DESC LIMIT 1",
        (assessment_id, user_id)).fetchone()
    conn.close()
    return row


def submit_attempt(assessment_id, user_id, answers):
    """
    Grade and save a new attempt.
    answers = {question_id: selected_index_as_string}
    Returns (attempt_id, score, max_score, passed).
    """
    assessment = get_assessment(assessment_id)
    if not assessment:
        return None, 0, 0, False

    # Attempt limit check
    prior = get_user_attempts(assessment_id, user_id)
    if len(prior) >= assessment["max_attempts"]:
        return None, 0, 0, False

    questions = get_assessment_questions(assessment_id)
    max_score = sum(q["points"] for q in questions)
    score = 0

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO assessment_attempts (assessment_id, user_id, attempt_number, "
        "score, max_score, passed) VALUES (?, ?, ?, ?, ?, ?)",
        (assessment_id, user_id, len(prior) + 1, 0, max_score, 0))
    attempt_id = cur.lastrowid

    for q in questions:
        selected = answers.get(str(q["id"]), "")
        is_correct = 1 if str(selected).strip() == str(q["correct_answer"]).strip() else 0
        awarded = q["points"] if is_correct else 0
        score += awarded
        cur.execute(
            "INSERT INTO assessment_responses (attempt_id, question_id, "
            "selected_answer, is_correct, points_awarded) VALUES (?, ?, ?, ?, ?)",
            (attempt_id, q["id"], str(selected), is_correct, awarded))

    passing = assessment["passing_score"]
    pct = (score * 100 // max_score) if max_score > 0 else 0
    passed = 1 if pct >= passing else 0

    cur.execute(
        "UPDATE assessment_attempts SET score = ?, max_score = ?, passed = ? "
        "WHERE id = ?", (score, max_score, passed, attempt_id))
    conn.commit()
    conn.close()

    # Auto-complete the linked lesson if passed
    if passed:
        mark_lesson_complete(user_id, assessment["lesson_id"])

    return attempt_id, score, max_score, bool(passed)


def get_attempt_details(attempt_id):
    """Get attempt + questions + user answers for the result page."""
    conn = get_connection()
    attempt = conn.execute(
        "SELECT * FROM assessment_attempts WHERE id = ?", (attempt_id,)).fetchone()
    if not attempt:
        conn.close()
        return None
    responses = conn.execute(
        "SELECT r.*, q.question_text, q.options_json, q.correct_answer, "
        "q.explanation, q.question_type, q.points, q.sequence_number "
        "FROM assessment_responses r "
        "JOIN assessment_questions q ON r.question_id = q.id "
        "WHERE r.attempt_id = ? ORDER BY q.sequence_number",
        (attempt_id,)).fetchall()
    conn.close()

    import json as _json
    items = []
    for r in responses:
        d = dict(r)
        try:
            d["options"] = _json.loads(d.get("options_json") or "[]")
        except Exception:
            d["options"] = []
        items.append(d)

    return {"attempt": dict(attempt), "responses": items}
def _seed_web_design_module2(cur):
    """Seed Module 2: Styling with CSS — 3 lessons + quiz."""
    import json as _json

    course = cur.execute(
        "SELECT id FROM academy_courses WHERE slug = 'web-design-development'"
    ).fetchone()
    if not course:
        return
    course_id = course["id"]

    # Check if module already exists
    existing = cur.execute(
        "SELECT id FROM course_modules WHERE course_id = ? AND title LIKE 'Module 2%'",
        (course_id,)).fetchone()

    if existing:
        module_id = existing["id"]
    else:
        cur.execute(
            "INSERT INTO course_modules (course_id, title, description, sequence_number) "
            "VALUES (?, ?, ?, ?)",
            (course_id, "Module 2: Styling with CSS",
             "Jifunze kupamba ukurasa wako kwa rangi, typography, box model, na Flexbox — kuunda layouts za kisasa.",
             2))
        module_id = cur.lastrowid

    lessons_data = [
        {
            "title": "CSS Basics & Selectors",
            "duration": 25,
            "objectives": [
                "Elewa CSS ni nini na kwa nini tunaihitaji",
                "Jua njia 3 za kuunganisha CSS kwenye HTML",
                "Tumia selectors: element, class, na id",
                "Elewa CSS rule anatomy (selector, property, value)",
            ],
            "sections": [
                {"type": "text", "title": "CSS ni nini?",
                 "body": "CSS (Cascading Style Sheets) ni lugha ya kupamba HTML. Bila CSS, ukurasa wako unaonekana kama hati ya Word ya 1995 — maandishi meusi kwenye background nyeupe, bila mpangilio. CSS inabadilisha rangi, ukubwa, nafasi, font, na kila kitu unachokiona kwenye tovuti za kisasa."},
                {"type": "callout", "title": "Mfano rahisi",
                 "body": "HTML = mifupa ya mwili (kichwa, mkono, mguu). CSS = ngozi, nywele, mavazi. Bila CSS, ungekuwa mifupa tu — inafanya kazi lakini haivutii. CSS inafanya ukurasa uwe mzuri na rahisi kutumia."},
                {"type": "text", "title": "Njia 3 za kuweka CSS",
                 "body": "Kuna njia 3: (1) Inline — ndani ya tag yenyewe (style='...'), (2) Internal — ndani ya <style> kwenye <head>, (3) External — faili tofauti la .css linalounganishwa na <link>. External ndiyo bora kwa miradi halisi — inaruhusu CSS moja kutumika kwenye kurasa nyingi."},
                {"type": "code", "title": "Njia 3 kwa mfano",
                 "language": "html",
                 "body": "",
                 "code": "<!-- 1. Inline -->\n<h1 style=\"color: red; font-size: 32px;\">Habari</h1>\n\n<!-- 2. Internal -->\n<head>\n  <style>\n    h1 { color: red; font-size: 32px; }\n  </style>\n</head>\n\n<!-- 3. External (inayopendekezwa) -->\n<head>\n  <link rel=\"stylesheet\" href=\"style.css\">\n</head>\n\n<!-- Kwenye style.css: -->\nh1 { color: red; font-size: 32px; }"},
                {"type": "text", "title": "Anatomia ya CSS rule",
                 "body": "Kila CSS rule ina sehemu 3: (1) Selector — kitu unachopamba (h1, .class, #id), (2) Property — kipengele unachobadilisha (color, font-size, margin), (3) Value — thamani mpya (red, 32px, 20px). Mfano: 'h1 { color: red; }' — hapa selector = h1, property = color, value = red."},
                {"type": "text", "title": "Selectors 3 muhimu",
                 "body": "Element selector: 'h1 { ... }' — inagusa vichwa VYOTE vya h1 kwenye ukurasa. Class selector: '.card { ... }' — inagusa vitu vyote vyenye class='card' (unaweza kutumia class mara nyingi). ID selector: '#header { ... }' — inagusa KITU KIMOJA tu chenye id='header' (id ni ya kipekee)."},
                {"type": "code", "title": "Mfano wa selectors",
                 "language": "css",
                 "body": "",
                 "code": "/* Element selector */\np { color: #333; line-height: 1.6; }\n\n/* Class selector (tumia . mwanzoni) */\n.highlight { background: yellow; padding: 4px; }\n\n/* ID selector (tumia # mwanzoni) */\n#main-title { font-size: 48px; color: #0B1F33; }\n\n/* HTML inayotumia: */\n<p>Maandishi ya kawaida</p>\n<p class=\"highlight\">Maandishi yaliyoangaziwa</p>\n<h1 id=\"main-title\">Kichwa Kikuu</h1>"},
                {"type": "callout", "title": "Class vs ID",
                 "body": "Tumia class kwa vitu vinavyorudiwa (cards, buttons, links). Tumia ID kwa kitu kimoja tu kwenye ukurasa (mfano: header kuu, form kuu). Class inaweza kutumika mara nyingi; ID mara moja tu kwa kila ukurasa."},
                {"type": "code", "title": "Rangi na typography za msingi",
                 "language": "css",
                 "body": "",
                 "code": "body {\n  font-family: 'Segoe UI', Arial, sans-serif;\n  color: #333333;\n  background: #f5f7fa;\n  font-size: 16px;\n  line-height: 1.6;\n}\n\nh1 {\n  color: #0B1F33;\n  font-size: 36px;\n  font-weight: 800;\n  margin-bottom: 16px;\n}"},
            ],
            "key_takeaways": [
                "CSS inapamba HTML — bila CSS, ukurasa ni maandishi tupu",
                "External CSS (faili .css) ndiyo njia bora kwa miradi halisi",
                "CSS rule = selector + property + value",
                "Class (.class) kwa vitu vinavyorudiwa; ID (#id) kwa kitu kimoja",
                "font-family, color, background, font-size ni properties za msingi",
            ],
            "common_mistakes": [
                {"mistake": "Kusahau semicolon (;) mwishoni mwa property",
                 "fix": "Kila property LAZIMA iishe na ';' — hata ya mwisho. Bila hiyo, CSS inavunjika."},
                {"mistake": "Kutumia dot (.) kwa ID au hash (#) kwa class",
                 "fix": "Class = '.class'; ID = '#id'. Kuchanganya = CSS haitafanya kazi."},
                {"mistake": "Kuweka CSS popote ndani ya <body>",
                 "fix": "CSS iko kwenye <style> ndani ya <head>, au faili tofauti linalounganishwa na <link> kwenye <head>."},
                {"mistake": "Kutumia inline style kwa kila kitu",
                 "fix": "Inline inaweza kwa kesi 1-2, lakini kwa mradi mzima tumia external CSS — ni rahisi kubadilisha na kudumisha."},
            ],
            "exercise_prompt": "Unda faili 'style.css' na uunganishe kwenye 'my-bio.html' (kutoka Module 1). Kwenye CSS: (1) weka body background #f5f7fa, font-family Segoe UI, (2) h1 rangi #0B1F33 na font-size 36px, (3) unda class '.highlight' yenye background yellow na padding 4px. Tumia class kwenye neno moja la maelezo yako.",
            "exercise_solution": "<!-- my-bio.html (head) -->\n<link rel=\"stylesheet\" href=\"style.css\">\n\n<!-- style.css -->\nbody {\n  background: #f5f7fa;\n  font-family: 'Segoe UI', Arial, sans-serif;\n  color: #333;\n  padding: 40px;\n}\n\nh1 {\n  color: #0B1F33;\n  font-size: 36px;\n  margin-bottom: 16px;\n}\n\n.highlight {\n  background: yellow;\n  padding: 4px;\n}\n\n<!-- my-bio.html (body) -->\n<h1>Amina Hassan</h1>\n<p>Mimi ni <span class=\"highlight\">mwanafunzi wa IT Level 4</span> ninayependa teknolojia.</p>",
        },

        {
            "title": "Box Model & Colors",
            "duration": 30,
            "objectives": [
                "Elewa box model: content, padding, border, margin",
                "Tumia box-sizing kudhibiti ukubwa wa elementi",
                "Jua aina 4 za rangi: jina, hex, rgb, rgba",
                "Tumia border-radius, box-shadow, na padding kwa ufanisi",
            ],
            "sections": [
                {"type": "text", "title": "Kila elementi ni box",
                 "body": "Kila kitu kwenye ukurasa wa wavuti ni box (sanduku) la mstatili. Hata kama unaona duara au maandishi — nyuma yake ni box. Box model ina sehemu 4: (1) Content — yaliyomo (maandishi, picha), (2) Padding — nafasi kati ya content na border, (3) Border — mstari unaozunguka padding, (4) Margin — nafasi kati ya box hii na box nyingine."},
                {"type": "callout", "title": "Mfano wa picha",
                 "body": "Fikiria fremu ya picha ukutani: picha yenyewe = content. Pengo jeupe kati ya picha na fremu = padding. Fremu ya mbao = border. Ukuta unaozunguka fremu = margin (nafasi kati ya fremu na samani nyingine)."},
                {"type": "code", "title": "Box model kwa mfano",
                 "language": "css",
                 "body": "",
                 "code": ".card {\n  /* Content (maandishi yaliyomo ndani) */\n  width: 300px;\n  \n  /* Padding: nafasi ndani ya box */\n  padding: 20px;\n  \n  /* Border: mstari unaozunguka */\n  border: 1px solid #e2e8f0;\n  border-radius: 12px;\n  \n  /* Margin: nafasi nje ya box */\n  margin: 16px auto;\n  \n  /* Background */\n  background: white;\n  \n  /* Shadow */\n  box-shadow: 0 4px 12px rgba(0,0,0,0.08);\n}"},
                {"type": "text", "title": "box-sizing: border-box — muhimu!",
                 "body": "Kwa default, width=300px inamaanisha CONTENT pekee. Ukiongeza padding 20px, box inakuwa 300 + 20 + 20 = 340px. Hii inasumbua. Suluhisho: weka 'box-sizing: border-box' — sasa width=300px inajumuisha padding na border. Kila mradi wa kisasa unatumia hii."},
                {"type": "code", "title": "Box-sizing kwenye CSS yote",
                 "language": "css",
                 "body": "Weka hii juu ya faili lako la CSS — inaathiri kila elementi:",
                 "code": "*, *::before, *::after {\n  box-sizing: border-box;\n}"},
                {"type": "text", "title": "Rangi — njia 4",
                 "body": "(1) Jina: red, blue, green (rahisi lakini chache). (2) Hex: #FF5733 (6 herufi/namba baada ya #). (3) RGB: rgb(255, 87, 51). (4) RGBA: rgba(255, 87, 51, 0.5) — yenye uwazi (0 = haionekani, 1 = imejaa). RGBA ni muhimu kwa overlays, hover effects, na glass effects."},
                {"type": "code", "title": "Mifano ya rangi",
                 "language": "css",
                 "body": "",
                 "code": "/* Jina */\nh1 { color: navy; }\n\n/* Hex (inayopendekezwa) */\np { color: #0B1F33; }\n\n/* RGB */\nbutton { background: rgb(244, 119, 33); }\n\n/* RGBA — kwa transparency */\n.overlay {\n  background: rgba(11, 31, 51, 0.7);\n}"},
                {"type": "callout", "title": "Tip: Jifunze hex",
                 "body": "Hex ina namba 0-9 na herufi A-F. #FFFFFF = nyeupe, #000000 = nyeusi, #F47721 = orange yetu. Unaweza kutumia color picker (mfano: coolors.co) kupata rangi nzuri."},
                {"type": "code", "title": "Card kamili ya kisasa",
                 "language": "css",
                 "body": "",
                 "code": ".card {\n  background: white;\n  padding: 24px;\n  border-radius: 12px;\n  border: 1px solid #e2e8f0;\n  box-shadow: 0 1px 3px rgba(0,0,0,0.05);\n  margin-bottom: 16px;\n  transition: box-shadow 0.2s;\n}\n\n.card:hover {\n  box-shadow: 0 8px 24px rgba(0,0,0,0.1);\n}"},
            ],
            "key_takeaways": [
                "Kila elementi ni box: content + padding + border + margin",
                "Daima weka '* { box-sizing: border-box; }' — inaepusha mahesabu magumu",
                "RGBA inaruhusu transparency — muhimu kwa overlays",
                "border-radius inafanya pembe kuwa mviringo",
                "box-shadow inaunda kivuli — inaongeza kina",
            ],
            "common_mistakes": [
                {"mistake": "Kuchanganya padding na margin",
                 "fix": "Padding = nafasi NDANI ya box (kati ya content na border). Margin = nafasi NJE ya box (kati ya box hii na nyingine)."},
                {"mistake": "Kusahau box-sizing: border-box",
                 "fix": "Weka kwenye CSS yote mwanzoni. Bila hiyo, padding na border zinaongeza ukubwa."},
                {"mistake": "Kutumia margin kuweka nafasi ndani ya box",
                 "fix": "Margin haitengenezi nafasi ndani ya box — inasogeza box nzima. Tumia padding kwa nafasi ndani."},
                {"mistake": "Kutumia rangi nyingi sana",
                 "fix": "Chagua rangi 2-3 kuu (primary, secondary, neutral) — usizidi 5 kwa mradi mzima."},
            ],
            "exercise_prompt": "Unda ukurasa 'products.html' wenye cards 3 za bidhaa. Kila card iwe na: background white, padding 20px, border-radius 12px, border 1px solid #e2e8f0, box-shadow laini. Ndani ya kila card: h3 (jina la bidhaa), p (maelezo), na button ya 'Nunua' yenye rangi ya orange #F47721. Ongeza hover effect inayoinua card.",
            "exercise_solution": "<!-- products.html -->\n<!DOCTYPE html>\n<html lang=\"sw\">\n<head>\n  <meta charset=\"UTF-8\">\n  <link rel=\"stylesheet\" href=\"style.css\">\n</head>\n<body>\n  <div class=\"products\">\n    <div class=\"card\">\n      <h3>Simu</h3>\n      <p>Simu janja ya kisasa</p>\n      <button>Nunua</button>\n    </div>\n    <div class=\"card\">\n      <h3>Laptop</h3>\n      <p>Kompyuta ya kubebeka</p>\n      <button>Nunua</button>\n    </div>\n    <div class=\"card\">\n      <h3>Headphones</h3>\n      <p>Vichwa vya kusikiliza</p>\n      <button>Nunua</button>\n    </div>\n  </div>\n</body>\n</html>\n\n<!-- style.css -->\n* { box-sizing: border-box; }\n\nbody {\n  font-family: 'Segoe UI', Arial, sans-serif;\n  background: #f5f7fa;\n  padding: 40px;\n}\n\n.products {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));\n  gap: 20px;\n}\n\n.card {\n  background: white;\n  padding: 20px;\n  border-radius: 12px;\n  border: 1px solid #e2e8f0;\n  box-shadow: 0 1px 3px rgba(0,0,0,0.05);\n  transition: box-shadow 0.2s, transform 0.2s;\n}\n\n.card:hover {\n  box-shadow: 0 8px 24px rgba(0,0,0,0.1);\n  transform: translateY(-2px);\n}\n\n.card h3 { margin: 0 0 8px; color: #0B1F33; }\n.card p { color: #64748b; margin: 0 0 16px; }\n\n.card button {\n  background: #F47721;\n  color: white;\n  border: none;\n  padding: 10px 20px;\n  border-radius: 8px;\n  font-weight: 700;\n  cursor: pointer;\n}\n\n.card button:hover { background: #e6670f; }",
        },

        {
            "title": "Layout with Flexbox",
            "duration": 30,
            "objectives": [
                "Elewa tofauti kati ya flex container na flex items",
                "Tumia justify-content kuweka vitu kwa usawa",
                "Tumia align-items kuweka vitu kwa wima",
                "Unda layout ya navigation bar na card grid",
            ],
            "sections": [
                {"type": "text", "title": "Flexbox ni nini?",
                 "body": "Flexbox ni mfumo wa CSS wa kupanga vitu kwa mstari au safu. Kabla ya Flexbox, ilikuwa ngumu kupanga vitu kwa usawa — watu walitumia floats, tables, na hacks. Flexbox inafanya iwe rahisi: unaiambia container 'panga watoto wako kwa mstari', na inafanya kazi."},
                {"type": "callout", "title": "Kanuni moja",
                 "body": "Kuweka 'display: flex' kwenye container — inageuza watoto WAKE WOTE kuwa flex items na kuwapanga kwa mstari (horizontal kwa default). Ndiyo yote. Rahisi."},
                {"type": "code", "title": "Flexbox ya msingi",
                 "language": "css",
                 "body": "",
                 "code": ".container {\n  display: flex;\n}\n\n<!-- HTML: -->\n<div class=\"container\">\n  <div>Kitu 1</div>\n  <div>Kitu 2</div>\n  <div>Kitu 3</div>\n</div>\n\n<!-- Matokeo: vitu 3 kwa mstari mmoja (horizontal) -->"},
                {"type": "text", "title": "justify-content — usawa wa horizontal",
                 "body": "flex-start (default) = kushoto. flex-end = kulia. center = katikati. space-between = kitu cha kwanza kushoto, cha mwisho kulia, vingine katikati. space-around = nafasi sawa kila upande. space-evenly = nafasi sawa kati ya vitu."},
                {"type": "code", "title": "justify-content kwa mifano",
                 "language": "css",
                 "body": "",
                 "code": "/* Vitu vikae katikati kwa usawa */\n.header {\n  display: flex;\n  justify-content: center;\n}\n\n/* Logo kushoto, menu kulia */\n.navbar {\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n}"},
                {"type": "text", "title": "align-items — usawa wa wima",
                 "body": "flex-start = juu. flex-end = chini. center = katikati (wima). stretch (default) = kunyoosha kujaza container. Hii ni muhimu kwa nav bars — unataka logo na menu viwe katikati kwa wima."},
                {"type": "text", "title": "gap — nafasi kati ya vitu",
                 "body": "Kabla ya gap, ilikuwa ngumu kuweka nafasi kati ya flex items. Sasa: 'gap: 16px' inaweka nafasi 16px kati ya kila kitu. Rahisi na safi."},
                {"type": "code", "title": "Navigation bar kamili",
                 "language": "css",
                 "body": "Hii ni nav bar ya kisasa — logo kushoto, menu kulia, kila kitu katikati kwa wima:",
                 "code": ".navbar {\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n  padding: 16px 24px;\n  background: #0B1F33;\n  color: white;\n}\n\n.nav-links {\n  display: flex;\n  gap: 16px;\n  list-style: none;\n}\n\n.nav-links a {\n  color: white;\n  text-decoration: none;\n  padding: 8px 12px;\n  border-radius: 6px;\n}\n\n.nav-links a:hover {\n  background: rgba(255,255,255,0.1);\n}"},
                {"type": "callout", "title": "flex-wrap — kama vitu ni vingi",
                 "body": "Kwa default, flex inajaribu kuweka vitu vyote kwenye mstari mmoja — hata kama vinapungua ukubwa. Ongeza 'flex-wrap: wrap' ili vitu viruke mstari mpya kama hakuna nafasi. Muhimu kwa cards na tags."},
                {"type": "code", "title": "Flexbox ya hali halisi",
                 "language": "css",
                 "body": "",
                 "code": "/* Card ya bidhaa */\n.product-card {\n  display: flex;\n  gap: 16px;\n  align-items: center;\n  padding: 16px;\n  background: white;\n  border-radius: 12px;\n}\n\n/* Picha upande wa kushoto, maelezo kulia */\n.product-card img {\n  width: 80px;\n  height: 80px;\n  object-fit: cover;\n  border-radius: 8px;\n}\n\n.product-info {\n  flex: 1;\n}\n\n/* Kitufe cha mwisho */\n.product-card button {\n  margin-left: auto;\n}"},
            ],
            "key_takeaways": [
                "display: flex inageuza container kuwa flexbox",
                "justify-content = usawa wa horizontal (kushoto, katikati, kulia, space-between)",
                "align-items = usawa wa wima (juu, katikati, chini)",
                "gap = nafasi kati ya vitu (rahisi kuliko margins)",
                "flex-wrap: wrap inaruhusu vitu kuruka mstari mpya",
                "flex: 1 inafanya kitu kujaza nafasi iliyobaki",
            ],
            "common_mistakes": [
                {"mistake": "Kuweka display: flex kwenye kila kitu",
                 "fix": "Weka display: flex tu kwenye container — watoto wake wanakuwa flex items automatically."},
                {"mistake": "Kuchanganya justify-content na align-items",
                 "fix": "justify-content = horizontal (mstari). align-items = wima (kwa mstari mmoja). Kumbuka: 'j' kwa 'ji' (upande), 'a' kwa 'altitude' (wima)."},
                {"mistake": "Kutumia margin kwa kila kitu kwenye flex",
                 "fix": "Tumia 'gap' kwa nafasi kati ya vitu — ni rahisi na safi."},
                {"mistake": "Kusahau flex-wrap kwa vitu vingi",
                 "fix": "Kama una cards 10, lazima 'flex-wrap: wrap' — vinginevyo vitapungua ukubwa hadi visionekane."},
            ],
            "exercise_prompt": "Unda ukurasa 'team.html' wenye: (1) navbar yenye logo kushoto na viungo 3 kulia, (2) sehemu ya 'Timu Yetu' yenye cards 4 za wanachama. Kila card iwe na picha, jina, cheo, na kitufe cha 'Wasiliana'. Tumia Flexbox kwa navbar na grid kwa cards.",
            "exercise_solution": "<!-- team.html -->\n<!DOCTYPE html>\n<html lang=\"sw\">\n<head>\n  <meta charset=\"UTF-8\">\n  <link rel=\"stylesheet\" href=\"style.css\">\n</head>\n<body>\n  <nav class=\"navbar\">\n    <div class=\"logo\">IT Expert</div>\n    <ul class=\"nav-links\">\n      <li><a href=\"#\">Nyumbani</a></li>\n      <li><a href=\"#\">Kuhusu</a></li>\n      <li><a href=\"#\">Wasiliana</a></li>\n    </ul>\n  </nav>\n\n  <section class=\"team\">\n    <h2>Timu Yetu</h2>\n    <div class=\"team-grid\">\n      <div class=\"member\">\n        <img src=\"https://picsum.photos/80\" alt=\"Mwanachama\">\n        <h3>Amina H.</h3>\n        <p>Mkurugenzi</p>\n        <button>Wasiliana</button>\n      </div>\n      <div class=\"member\">\n        <img src=\"https://picsum.photos/81\" alt=\"Mwanachama\">\n        <h3>John M.</h3>\n        <p>Msanidi</p>\n        <button>Wasiliana</button>\n      </div>\n      <div class=\"member\">\n        <img src=\"https://picsum.photos/82\" alt=\"Mwanachama\">\n        <h3>Grace K.</h3>\n        <p>Mbunifu</p>\n        <button>Wasiliana</button>\n      </div>\n      <div class=\"member\">\n        <img src=\"https://picsum.photos/83\" alt=\"Mwanachama\">\n        <h3>Peter S.</h3>\n        <p>Mhandisi</p>\n        <button>Wasiliana</button>\n      </div>\n    </div>\n  </section>\n</body>\n</html>\n\n<!-- style.css -->\n* { box-sizing: border-box; }\n\nbody {\n  font-family: 'Segoe UI', Arial, sans-serif;\n  background: #f5f7fa;\n  margin: 0;\n}\n\n.navbar {\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n  padding: 16px 24px;\n  background: #0B1F33;\n  color: white;\n}\n\n.logo { font-weight: 800; font-size: 18px; }\n\n.nav-links {\n  display: flex;\n  gap: 16px;\n  list-style: none;\n  margin: 0;\n  padding: 0;\n}\n\n.nav-links a {\n  color: white;\n  text-decoration: none;\n  padding: 8px 12px;\n  border-radius: 6px;\n}\n\n.nav-links a:hover { background: rgba(255,255,255,0.1); }\n\n.team { padding: 60px 24px; max-width: 1100px; margin: 0 auto; }\n.team h2 { text-align: center; color: #0B1F33; font-size: 32px; margin-bottom: 32px; }\n\n.team-grid {\n  display: grid;\n  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));\n  gap: 20px;\n}\n\n.member {\n  background: white;\n  padding: 24px;\n  border-radius: 12px;\n  text-align: center;\n  box-shadow: 0 1px 3px rgba(0,0,0,0.05);\n}\n\n.member img {\n  width: 80px;\n  height: 80px;\n  border-radius: 50%;\n  margin-bottom: 12px;\n}\n\n.member h3 { margin: 0 0 4px; color: #0B1F33; }\n.member p { color: #64748b; margin: 0 0 16px; }\n\n.member button {\n  background: #F47721;\n  color: white;\n  border: none;\n  padding: 8px 16px;\n  border-radius: 6px;\n  cursor: pointer;\n  font-weight: 700;\n}\n\n.member button:hover { background: #e6670f; }",
        },
    ]

    for li, lesson in enumerate(lessons_data, 1):
        existing = cur.execute(
            "SELECT id FROM lessons WHERE module_id = ? AND title = ?",
            (module_id, lesson["title"])).fetchone()
        if existing:
            continue

        html_fallback = f"<h2>{lesson['title']}</h2>"
        html_fallback += "<h3>Malengo ya Somo</h3><ul>"
        for obj in lesson["objectives"]:
            html_fallback += f"<li>{obj}</li>"
        html_fallback += "</ul>"

        cur.execute(
            "INSERT INTO lessons (module_id, title, content, lesson_type, "
            "sequence_number, estimated_duration_min, status, "
            "objectives_json, sections_json, key_takeaways_json, "
            "common_mistakes_json, exercise_prompt, exercise_solution, "
            "module_order, lesson_order) "
            "VALUES (?, ?, ?, 'text', ?, ?, 'published', ?, ?, ?, ?, ?, ?, ?, ?)",
            (module_id, lesson["title"], html_fallback, li,
             lesson["duration"], li,
             _json.dumps(lesson["objectives"], ensure_ascii=False),
             _json.dumps(lesson["sections"], ensure_ascii=False),
             _json.dumps(lesson["key_takeaways"], ensure_ascii=False),
             _json.dumps(lesson["common_mistakes"], ensure_ascii=False),
             lesson["exercise_prompt"],
             lesson["exercise_solution"],
             2, li))

    # Quiz 2
    existing_quiz = cur.execute(
        "SELECT id FROM assessments WHERE title LIKE 'Module 2%' LIMIT 1"
    ).fetchone()
    if not existing_quiz:
        first_lesson = cur.execute(
            "SELECT id FROM lessons WHERE module_id = ? ORDER BY sequence_number LIMIT 1",
            (module_id,)).fetchone()
        if first_lesson:
            cur.execute(
                "INSERT INTO assessments (lesson_id, title, description, passing_score, max_attempts) "
                "VALUES (?, ?, ?, ?, ?)",
                (first_lesson["id"], "Module 2 Quiz: Styling with CSS",
                 "Jaribu uelewa wako wa CSS selectors, box model, na Flexbox.",
                 70, 3))
            aid = cur.lastrowid
            questions = [
                ("multiple_choice", "CSS inatumika kwa nini?",
                 ["Kupamba na kupanga muonekano wa HTML", "Kuunda muundo wa HTML",
                  "Kuendesha server", "Kuhifadhi data"], "0",
                 "CSS = kupamba. HTML = muundo. JavaScript = tabia.", 10),
                ("multiple_choice", "Ni selector ipi inagusa class='card'?",
                 ["card", ".card", "#card", "*card"], "1",
                 "Class inaanza na '.'. ID inaanza na '#'.", 10),
                ("multiple_choice", "Nafasi NDANI ya box (kati ya content na border) inaitwa nini?",
                 ["Margin", "Padding", "Border", "Gap"], "1",
                 "Padding = ndani. Margin = nje. Border = mstari.", 10),
                ("true_false", "box-sizing: border-box inafanya width ijumuishe padding na border.",
                 ["True", "False"], "0",
                 "Kweli. Bila hii, padding na border zinaongeza ukubwa.", 10),
                ("multiple_choice", "Ni property ipi inaweka vitu katikati kwa usawa (horizontal)?",
                 ["align-items: center", "justify-content: center",
                  "text-align: center", "flex-direction: row"], "1",
                 "justify-content = horizontal. align-items = wima.", 10),
            ]
            for qi, (qtype, qtext, opts, correct, expl, pts) in enumerate(questions, 1):
                cur.execute(
                    "INSERT INTO assessment_questions (assessment_id, question_type, "
                    "question_text, options_json, correct_answer, explanation, "
                    "points, sequence_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (aid, qtype, qtext, _json.dumps(opts, ensure_ascii=False),
                     correct, expl, pts, qi))

# ============================================================
# AI TUTOR (Phase 4)
# ============================================================
def init_ai_tables():
    """Create AI tutor tables (safe to run repeatedly)."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tutor_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        course_id INTEGER,
        lesson_id INTEGER,
        title TEXT DEFAULT 'New Chat',
        language TEXT DEFAULT 'sw',
        teaching_mode TEXT DEFAULT 'explain',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tutor_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        sender_type TEXT NOT NULL,
        content TEXT NOT NULL,
        model_name TEXT,
        tokens_input INTEGER DEFAULT 0,
        tokens_output INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (conversation_id) REFERENCES tutor_conversations(id) ON DELETE CASCADE
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ai_usage_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        conversation_id INTEGER,
        tokens_input INTEGER DEFAULT 0,
        tokens_output INTEGER DEFAULT 0,
        cost_usd REAL DEFAULT 0,
        recorded_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    conn.commit()
    conn.close()


def create_conversation(user_id, lesson_id=None, course_id=None,
                        language="sw", teaching_mode="explain", title="New Chat"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tutor_conversations (user_id, lesson_id, course_id, "
        "language, teaching_mode, title) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, lesson_id, course_id, language, teaching_mode, title))
    conv_id = cur.lastrowid
    conn.commit()
    conn.close()
    return conv_id


def get_conversation(conv_id, user_id=None):
    conn = get_connection()
    if user_id is not None:
        row = conn.execute(
            "SELECT * FROM tutor_conversations WHERE id = ? AND user_id = ?",
            (conv_id, user_id)).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM tutor_conversations WHERE id = ?", (conv_id,)).fetchone()
    conn.close()
    return row


def get_user_conversations(user_id, limit=30):
    conn = get_connection()
    rows = conn.execute(
        "SELECT c.*, "
        "(SELECT COUNT(*) FROM tutor_messages WHERE conversation_id = c.id) AS msg_count "
        "FROM tutor_conversations c WHERE c.user_id = ? "
        "ORDER BY c.updated_at DESC LIMIT ?",
        (user_id, limit)).fetchall()
    conn.close()
    return rows


def get_messages(conv_id, limit=100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tutor_messages WHERE conversation_id = ? "
        "ORDER BY id ASC LIMIT ?", (conv_id, limit)).fetchall()
    conn.close()
    return rows


def add_message(conv_id, sender_type, content, model_name=None,
                tokens_input=0, tokens_output=0):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tutor_messages (conversation_id, sender_type, content, "
        "model_name, tokens_input, tokens_output) VALUES (?, ?, ?, ?, ?, ?)",
        (conv_id, sender_type, content, model_name, tokens_input, tokens_output))
    msg_id = cur.lastrowid
    cur.execute(
        "UPDATE tutor_conversations SET updated_at = datetime('now','localtime') "
        "WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()
    return msg_id


def update_conversation_settings(conv_id, language=None, teaching_mode=None):
    conn = get_connection()
    if language:
        conn.execute("UPDATE tutor_conversations SET language = ? WHERE id = ?",
                     (language, conv_id))
    if teaching_mode:
        conn.execute("UPDATE tutor_conversations SET teaching_mode = ? WHERE id = ?",
                     (teaching_mode, conv_id))
    conn.commit()
    conn.close()


def delete_conversation(conv_id, user_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM tutor_conversations WHERE id = ? AND user_id = ?",
        (conv_id, user_id))
    conn.commit()
    conn.close()


def record_ai_usage(user_id, conv_id, tokens_input, tokens_output, cost_usd):
    conn = get_connection()
    conn.execute(
        "INSERT INTO ai_usage_records (user_id, conversation_id, tokens_input, "
        "tokens_output, cost_usd) VALUES (?, ?, ?, ?, ?)",
        (user_id, conv_id, tokens_input, tokens_output, cost_usd))
    conn.commit()
    conn.close()


def get_today_ai_usage(user_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(COUNT(*), 0) AS count "
        "FROM ai_usage_records WHERE user_id = ? AND DATE(recorded_at) = DATE('now','localtime')",
        (user_id,)).fetchone()
    conn.close()
    return row["count"] if row else 0


# ============================================================
# CODING LAB (Phase 5)
# ============================================================
def init_coding_tables():
    """Create coding lab tables (idempotent)."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS coding_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_user_id INTEGER NOT NULL,
        course_id INTEGER,
        lesson_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        language TEXT NOT NULL,
        code_content TEXT,
        visibility TEXT DEFAULT 'private',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )""")

    conn.commit()
    conn.close()


STARTER_CODE = {
    "html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>My Page</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #f5f7fa;
      color: #0B1F33;
      padding: 40px;
      text-align: center;
    }
    h1 { color: #F47721; }
    button {
      background: #F47721;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 16px;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <h1>Habari, Dunia! 👋</h1>
  <p>Badilisha code hii na uone matokeo papo hapo.</p>
  <button onclick="alert('Umebonyeza!')">Bonyeza Mimi</button>
</body>
</html>
""",
    "javascript": """// JavaScript Playground
// Output itaonekana kwenye console hapa chini

console.log("Habari, Dunia!");

let jina = "Amina";
let umri = 20;

console.log(`Jina langu ni ${jina}, nina miaka ${umri}.`);

function salamu(jina) {
  return `Karibu, ${jina}!`;
}

console.log(salamu("Mwanafunzi"));
""",
    "python": """# Python Playground
# Inaendesha kwenye browser kwa Pyodide

print("Habari, Dunia!")

jina = "Amina"
umri = 20

print(f"Jina langu ni {jina}, nina miaka {umri}.")

def salamu(jina):
    return f"Karibu, {jina}!"

print(salamu("Mwanafunzi"))
""",
}


def create_project(user_id, title, language, code=None, description="",
                   course_id=None, lesson_id=None):
    """Create a new coding project."""
    if language not in STARTER_CODE:
        return None
    code = code if code else STARTER_CODE[language]
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO coding_projects (owner_user_id, course_id, lesson_id, "
        "title, description, language, code_content) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, course_id, lesson_id, title, description, language, code))
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def get_project(pid, user_id):
    """Get a project owned by this user."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM coding_projects WHERE id = ? AND owner_user_id = ?",
        (pid, user_id)).fetchone()
    conn.close()
    return row


def get_user_projects(user_id, limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, language, updated_at, "
        "LENGTH(code_content) AS code_size "
        "FROM coding_projects WHERE owner_user_id = ? "
        "ORDER BY updated_at DESC LIMIT ?",
        (user_id, limit)).fetchall()
    conn.close()
    return rows


def save_project(pid, user_id, code):
    conn = get_connection()
    conn.execute(
        "UPDATE coding_projects SET code_content = ?, "
        "updated_at = datetime('now','localtime') "
        "WHERE id = ? AND owner_user_id = ?",
        (code, pid, user_id))
    conn.commit()
    conn.close()


def rename_project(pid, user_id, new_title):
    conn = get_connection()
    conn.execute(
        "UPDATE coding_projects SET title = ?, "
        "updated_at = datetime('now','localtime') "
        "WHERE id = ? AND owner_user_id = ?",
        (new_title, pid, user_id))
    conn.commit()
    conn.close()


def delete_project(pid, user_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM coding_projects WHERE id = ? AND owner_user_id = ?",
        (pid, user_id))
    conn.commit()
    conn.close()
def _seed_course_placeholders(cur):
    """Seed all 19 courses from the Master Curriculum. Python already published; others coming_soon."""
    all_courses = [
        # COMPUTER & DIGITAL SKILLS
        ("computer-fundamentals", "Computer Fundamentals", "computer-foundations", "Beginner", 180,
         "Computer basics, Windows, files, folders, software, troubleshooting na computer maintenance."),
        ("microsoft-office", "Microsoft Office & Productivity", "computer-foundations", "Beginner", 240,
         "Microsoft Word, Excel, PowerPoint, professional documents, spreadsheets na presentations."),
        ("internet-digital-work", "Internet, Digital Communication & Online Work", "computer-foundations", "Beginner", 150,
         "Email, cloud storage, online collaboration, research, remote work na digital professionalism."),

        # SOFTWARE & PROGRAMMING
        ("web-design-development", "Web Design & Development", "programming-foundations", "Beginner", 300,
         "HTML, CSS, JavaScript, responsive websites na frontend development."),
        ("modern-frontend", "Modern Frontend Development", "programming-foundations", "Intermediate", 320,
         "React, components, application interfaces, APIs, state management na modern web applications."),
        ("backend-apis", "Backend Development & APIs", "programming-foundations", "Intermediate", 300,
         "Server-side programming, REST APIs, authentication, validation na application architecture."),
        ("database-management-sql", "Database Management & SQL", "programming-foundations", "Intermediate", 240,
         "Database design, SQL, PostgreSQL, relationships, queries, backups na data security."),

        # AI & DATA
        ("ai-tools", "AI & AI Tools", "ai-assisted-development", "Beginner", 180,
         "AI fundamentals, ChatGPT, AI productivity, prompting, responsible AI na matumizi ya AI kazini."),
        ("ai-powered-dev", "AI-Powered Software Development", "ai-assisted-development", "Intermediate", 300,
         "Kutumia AI kujenga applications, kuelewa code, debugging, testing na project development."),
        ("data-analytics", "Data Analytics & Visualization", "ai-assisted-development", "Intermediate", 280,
         "Excel advanced, SQL, Power BI, data cleaning, dashboards na data interpretation."),
        ("data-science-ml", "Data Science & Machine Learning", "ai-assisted-development", "Advanced", 360,
         "Python for data, statistics, data preparation, machine learning fundamentals na practical models."),

        # NETWORKING, SECURITY & INFRASTRUCTURE
        ("networking-it-support", "Computer Networking & IT Support", "web-development", "Beginner", 240,
         "Networking fundamentals, IP addressing, routers, switches, troubleshooting na IT support."),
        ("cybersecurity-fundamentals", "Cybersecurity Fundamentals", "web-development", "Beginner", 240,
         "Digital security, network security, access control, threat awareness, safe systems na incident response."),
        ("linux-server", "Linux & Server Administration", "web-development", "Intermediate", 300,
         "Linux commands, users, permissions, services, server configuration, Nginx na basic deployment."),
        ("cloud-devops", "Cloud Computing & DevOps", "web-development", "Advanced", 320,
         "Cloud fundamentals, deployment, Docker, CI/CD, monitoring na infrastructure management."),

        # DIGITAL BUSINESS & CREATIVE
        ("digital-marketing", "Digital Marketing & E-Commerce", "databases-backend", "Beginner", 220,
         "Social media marketing, online branding, digital advertising, online stores na customer engagement."),
        ("graphic-design", "Graphic Design & Digital Content", "databases-backend", "Beginner", 240,
         "Canva, design fundamentals, branding, image editing, video editing na content production."),
        ("it-project-management", "IT Project Management", "databases-backend", "Intermediate", 200,
         "Requirements, project planning, Agile fundamentals, teamwork, documentation na project delivery."),
    ]

    for slug, title, cat_slug, diff, mins, desc in all_courses:
        cat = cur.execute(
            "SELECT id FROM learning_paths WHERE slug = ?", (cat_slug,)
        ).fetchone()
        if not cat:
            continue
        existing = cur.execute(
            "SELECT id FROM academy_courses WHERE slug = ?", (slug,)
        ).fetchone()
        if existing:
            cur.execute(
                "UPDATE academy_courses SET learning_path_id=?, title=?, "
                "description=?, difficulty_level=?, estimated_duration_min=? "
                "WHERE slug=?",
                (cat["id"], title, desc, diff, mins, slug))
        else:
            cur.execute(
                "INSERT INTO academy_courses "
                "(learning_path_id, title, slug, description, difficulty_level, "
                "language, estimated_duration_min, status) "
                "VALUES (?, ?, ?, ?, ?, 'sw', ?, 'coming_soon')",
                (cat["id"], title, slug, desc, diff, mins))


# ============================================================
# CAREER LEARNING PATHS (Modification 2)
# ============================================================
def init_career_tables():
    """Create career_paths tables and seed them."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS career_paths (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        role_target TEXT,
        description TEXT,
        icon TEXT,
        color TEXT,
        sequence_number INTEGER DEFAULT 1,
        status TEXT DEFAULT 'active'
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS career_path_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        career_id INTEGER NOT NULL,
        course_id INTEGER NOT NULL,
        sequence_number INTEGER DEFAULT 1,
        is_required INTEGER DEFAULT 1,
        notes TEXT,
        FOREIGN KEY (career_id) REFERENCES career_paths(id) ON DELETE CASCADE,
        FOREIGN KEY (course_id) REFERENCES academy_courses(id) ON DELETE CASCADE,
        UNIQUE(career_id, course_id)
    )""")

    conn.commit()
    _seed_career_paths(cur)
    _seed_web_design_module1(cur)
    _seed_web_design_module1(cur)
    conn.commit()
    conn.close()


def _seed_career_paths(cur):
    """Seed 5 career paths linked to courses by slug."""
    careers = [
        {
            "slug": "web-developer",
            "title": "Become a Web Developer",
            "role_target": "Web Developer",
            "icon": "🌐",
            "color": "#2563EB",
            "description": "Jenga tovuti na web applications za kisasa — kuanzia HTML/CSS hadi backend na database. Ujuzi wa kuajiriwa kama Web Developer.",
            "courses": [
                ("web-design-development", 1, 1),
                ("modern-frontend", 2, 1),
                ("backend-apis", 3, 1),
                ("database-management-sql", 4, 1),
                ("it-project-management", 5, 0),
            ],
        },
        {
            "slug": "data-analyst",
            "title": "Become a Data Analyst",
            "role_target": "Data Analyst",
            "icon": "📊",
            "color": "#7C3AED",
            "description": "Jifunze kuchambua data, kujenga dashboards, na kufanya maamuzi kwa data. Ujuzi wa kuajiriwa kama Data Analyst.",
            "courses": [
                ("microsoft-office", 1, 1),
                ("data-analytics", 2, 1),
                ("database-management-sql", 3, 1),
                ("python-fundamentals-101", 4, 1),
                ("data-science-ml", 5, 0),
            ],
        },
        {
            "slug": "ai-developer",
            "title": "Become an AI-Assisted Developer",
            "role_target": "AI-Assisted Developer",
            "icon": "🤖",
            "color": "#F47721",
            "description": "Tumia AI kujenga software haraka na kwa ubora. Ujuzi wa kisasa unaotafutwa na waajiri wengi leo.",
            "courses": [
                ("computer-fundamentals", 1, 1),
                ("python-fundamentals-101", 2, 1),
                ("ai-tools", 3, 1),
                ("ai-powered-dev", 4, 1),
                ("database-management-sql", 5, 0),
            ],
        },
        {
            "slug": "cybersecurity",
            "title": "Become a Cybersecurity Specialist",
            "role_target": "Cybersecurity Specialist",
            "icon": "🔒",
            "color": "#0E8F78",
            "description": "Linda mifumo ya kidijitali dhidi ya vitisho. Ujuzi wa usalama wa mtandao unaohitajika sana nchini.",
            "courses": [
                ("computer-fundamentals", 1, 1),
                ("networking-it-support", 2, 1),
                ("cybersecurity-fundamentals", 3, 1),
                ("linux-server", 4, 1),
                ("cloud-devops", 5, 0),
            ],
        },
        {
            "slug": "it-support",
            "title": "Become an IT Support Technician",
            "role_target": "IT Support Technician",
            "icon": "💻",
            "color": "#DC2626",
            "description": "Saidia watumiaji na mifumo ya kompyuta. Kazi nyingi za IT Support zinapatikana kila siku Tanzania.",
            "courses": [
                ("computer-fundamentals", 1, 1),
                ("microsoft-office", 2, 1),
                ("networking-it-support", 3, 1),
                ("cybersecurity-fundamentals", 4, 0),
            ],
        },
    ]

    for seq, c in enumerate(careers, 1):
        existing = cur.execute(
            "SELECT id FROM career_paths WHERE slug = ?", (c["slug"],)
        ).fetchone()
        if existing:
            cur.execute(
                "UPDATE career_paths SET title=?, role_target=?, description=?, "
                "icon=?, color=?, sequence_number=? WHERE slug=?",
                (c["title"], c["role_target"], c["description"],
                 c["icon"], c["color"], seq, c["slug"]))
            career_id = existing["id"]
        else:
            cur.execute(
                "INSERT INTO career_paths (slug, title, role_target, description, "
                "icon, color, sequence_number) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (c["slug"], c["title"], c["role_target"],
                 c["description"], c["icon"], c["color"], seq))
            career_id = cur.lastrowid

        # Link courses
        cur.execute(
            "DELETE FROM career_path_courses WHERE career_id = ?", (career_id,))
        for course_slug, course_seq, is_required in c["courses"]:
            course = cur.execute(
                "SELECT id FROM academy_courses WHERE slug = ?", (course_slug,)
            ).fetchone()
            if course:
                cur.execute(
                    "INSERT INTO career_path_courses (career_id, course_id, "
                    "sequence_number, is_required) VALUES (?, ?, ?, ?)",
                    (career_id, course["id"], course_seq, is_required))


def get_all_career_paths():
    conn = get_connection()
    rows = conn.execute(
        "SELECT cp.*, "
        "(SELECT COUNT(*) FROM career_path_courses WHERE career_id = cp.id) AS course_count "
        "FROM career_paths cp WHERE cp.status = 'active' "
        "ORDER BY cp.sequence_number").fetchall()
    conn.close()
    return rows


def get_career_path(slug):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM career_paths WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    return row


def get_career_courses(career_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT cpc.*, "
        "c.title, c.slug, c.description, c.difficulty_level, "
        "c.estimated_duration_min, c.status, "
        "c.id AS course_id, "
        "p.icon AS path_icon, p.color AS path_color, p.title AS path_title "
        "FROM career_path_courses cpc "
        "JOIN academy_courses c ON cpc.course_id = c.id "
        "JOIN learning_paths p ON c.learning_path_id = p.id "
        "WHERE cpc.career_id = ? "
        "ORDER BY cpc.sequence_number", (career_id,)).fetchall()
    conn.close()
    return rows


def get_user_career_progress(user_id, career_id):
    """Return (completed_courses, total_courses) for a user."""
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) FROM career_path_courses WHERE career_id = ?",
        (career_id,)).fetchone()[0]
    if total == 0:
        conn.close()
        return 0, 0
    # Completed = course has a certificate
    completed = conn.execute(
        "SELECT COUNT(*) FROM career_path_courses cpc "
        "JOIN certificates cert ON cert.course_id = cpc.course_id "
        "WHERE cpc.career_id = ? AND cert.user_id = ?",
        (career_id, user_id)).fetchone()[0]
    conn.close()
    return completed, total


# ============================================================
# MASTERY GATING (Modification 3)
# ============================================================
def is_lesson_unlocked(user_id, lesson):
    """Check if user has unlocked this lesson (progressive unlock)."""
    if not lesson:
        return False
    if not is_enrolled(user_id, lesson["course_id"]):
        return False

    conn = get_connection()

    # Get all lessons in same module ordered
    same_module = conn.execute(
        "SELECT id, sequence_number FROM lessons "
        "WHERE module_id = ? AND status = 'published' "
        "ORDER BY sequence_number",
        (lesson["module_id"],)).fetchall()

    current_pos = None
    for i, l in enumerate(same_module):
        if l["id"] == lesson["id"]:
            current_pos = i
            break

    if current_pos is None:
        conn.close()
        return False

    # First lesson in module — check previous modules' completion
    if current_pos == 0:
        mod = conn.execute(
            "SELECT course_id, sequence_number FROM course_modules WHERE id = ?",
            (lesson["module_id"],)).fetchone()
        prev_modules = conn.execute(
            "SELECT id FROM course_modules WHERE course_id = ? "
            "AND sequence_number < ? ORDER BY sequence_number",
            (mod["course_id"], mod["sequence_number"])).fetchall()

        for pm in prev_modules:
            incomplete = conn.execute(
                "SELECT COUNT(*) FROM lessons l "
                "WHERE l.module_id = ? AND l.status = 'published' "
                "AND l.id NOT IN (SELECT lesson_id FROM lesson_progress "
                "WHERE user_id = ? AND status = 'completed')",
                (pm["id"], user_id)).fetchone()[0]
            if incomplete > 0:
                conn.close()
                return False
        conn.close()
        return True

    # Not first — check previous lesson completed
    prev_id = same_module[current_pos - 1]["id"]
    prev = conn.execute(
        "SELECT status FROM lesson_progress WHERE user_id = ? AND lesson_id = ?",
        (user_id, prev_id)).fetchone()
    conn.close()
    return prev is not None and prev["status"] == "completed"


def get_lesson_lock_info(user_id, lesson):
    """Returns dict with lock status + reason for UI."""
    if is_lesson_unlocked(user_id, lesson):
        return {"locked": False, "reason": None}

    conn = get_connection()
    same_module = conn.execute(
        "SELECT id, title, sequence_number FROM lessons "
        "WHERE module_id = ? AND status = 'published' "
        "ORDER BY sequence_number", (lesson["module_id"],)).fetchall()

    for i, l in enumerate(same_module):
        if l["id"] == lesson["id"] and i > 0:
            conn.close()
            return {
                "locked": True,
                "reason": f"Maliza somo la awali: '{same_module[i-1]['title']}'",
            }
    conn.close()
    return {"locked": True, "reason": "Maliza masomo ya moduli iliyopita kwanza."}


def get_module_progress(user_id, module_id):
    """Return (completed_count, total_count) for a module."""
    conn = get_connection()
    total = conn.execute(
        "SELECT COUNT(*) FROM lessons WHERE module_id = ? AND status = 'published'",
        (module_id,)).fetchone()[0]
    done = conn.execute(
        "SELECT COUNT(*) FROM lesson_progress lp "
        "JOIN lessons l ON lp.lesson_id = l.id "
        "WHERE l.module_id = ? AND lp.user_id = ? AND lp.status = 'completed'",
        (module_id, user_id)).fetchone()[0]
    conn.close()
    return done, total