# Evaluation question set for the RAGAS harness.
# Reduced to 15 questions (3 per lecture).

EVAL_QUESTIONS = [
    # -------------------------------------------------------------------------
    # Lecture 1: Introduction to AI
    # -------------------------------------------------------------------------
    {
        "question": "What is the distinction between autonomous behavior and adaptive behavior in an AI agent?",
        "reference": "Autonomous behavior means the system does not require constant instructions to operate, whereas adaptive behavior means the system can modify its behavior when the environment or problem space changes[cite: 2].",
        "expected_source": "CSE281_Lecture 1.pdf"
    },
    {
        "question": "What are the four levels of the DIKW Pyramid and how are they defined?",
        "reference": "The four levels are: Data (unorganized, unprocessed raw facts), Information (aggregated data that provides context and answers questions), Knowledge (information combined with human experience and context), and Wisdom (the ability to make sound decisions using knowledge)[cite: 2].",
        "expected_source": "CSE281_Lecture 1.pdf"
    },
    {
        "question": "What are the core differences between Supervised, Unsupervised, and Reinforcement Learning?",
        "reference": "Supervised learning uses labeled training data with known outcomes; Unsupervised learning uncovers hidden patterns and structures in unlabeled data; Reinforcement learning trains agents through trial and error using rewards for desired actions and penalties for unfavorable ones[cite: 2].",
        "expected_source": "CSE281_Lecture 1.pdf"
    },

    # -------------------------------------------------------------------------
    # Lecture 2: Search Algorithms
    # -------------------------------------------------------------------------
    {
        "question": "What are the five core components required to formally define a search problem?",
        "reference": "A search problem is defined by an initial state, a set of available actions, a transition model RESULT(s, a), a goal test, and a path cost function[cite: 3].",
        "expected_source": "CSE281_Lecture 2.pdf"
    },
    {
        "question": "What is the evaluation function of A* search, and under what condition is A* guaranteed to be optimal?",
        "reference": "A* search evaluates nodes using f(n) = g(n) + h(n), where g(n) is the exact cost to reach node n and h(n) is the estimated cost to the goal. It is optimal provided h(n) is an admissible heuristic (it never overestimates the actual cost)[cite: 3].",
        "expected_source": "CSE281_Lecture 2.pdf"
    },
    {
        "question": "When should Manhattan distance be used as a heuristic instead of Euclidean distance in grid-based pathfinding?",
        "reference": "Manhattan distance should be used when movement is restricted to 4 directions (up, down, left, right), whereas Euclidean distance is appropriate when movement is allowed in any direction[cite: 3].",
        "expected_source": "CSE281_Lecture 2.pdf"
    },

    # -------------------------------------------------------------------------
    # Lecture 3: Adversarial Search
    # -------------------------------------------------------------------------
    {
        "question": "What is the key structural difference between a simultaneous game and a sequential game?",
        "reference": "In a simultaneous game, players make their moves at the same time without knowledge of the choices made by others, whereas in a sequential game, players take turns making moves and can observe previous actions[cite: 4].",
        "expected_source": "CSE281_Lecture 3.pdf"
    },
    {
        "question": "What defines a zero-sum game in game theory?",
        "reference": "A zero-sum game is one where the total sum of payoffs across all players equals zero for every outcome, meaning any gain for one player results in an equal loss for another player[cite: 4].",
        "expected_source": "CSE281_Lecture 3.pdf"
    },
    {
        "question": "What general condition triggers pruning in the Alpha-Beta Pruning algorithm?",
        "reference": "Pruning occurs whenever the alpha value at a node is greater than or equal to the beta value of an ancestor node (alpha >= beta), meaning the current branch cannot influence the final outcome at the root[cite: 4].",
        "expected_source": "CSE281_Lecture 3.pdf"
    },

    # -------------------------------------------------------------------------
    # Lecture 4: Knowledge Representation & Reasoning (KRR)
    # -------------------------------------------------------------------------
    {
        "question": "How does declarative knowledge differ from procedural knowledge?",
        "reference": "Declarative knowledge represents explicit static facts and information answering 'what' questions, whereas procedural knowledge represents step-by-step operational instructions and algorithms answering 'how' to perform tasks[cite: 5].",
        "expected_source": "CSE281_Lecture 4.pdf"
    },
    {
        "question": "How is knowledge structured inside a Frame representation?",
        "reference": "A Frame encapsulates structured knowledge about stereotypical objects or situations using named attributes called 'slots' and corresponding values or constraints called 'filters'[cite: 5].",
        "expected_source": "CSE281_Lecture 4.pdf"
    },
    {
        "question": "What is the expressive advantage of First-Order Logic (FOL) over Propositional Logic?",
        "reference": "Propositional logic treats basic facts as atomic propositions that are simply true or false, whereas First-Order Logic expresses complex relationships using objects, predicates, functions, and universal or existential quantifiers[cite: 5].",
        "expected_source": "CSE281_Lecture 4.pdf"
    },

    # -------------------------------------------------------------------------
    # Lecture 5: Matrix Games & Logic Applications
    # -------------------------------------------------------------------------
    {
        "question": "What is a Saddle Point in a zero-sum payoff matrix game?",
        "reference": "A Saddle Point is an entry in a payoff matrix that is simultaneously the minimum element in its row and the maximum element in its column, establishing the strict value of the game[cite: 1].",
        "expected_source": "CSE281_Lecture 5.pdf"
    },
    {
        "question": "What is the effect of removing a strictly dominated strategy on a matrix game?",
        "reference": "Removing a strictly dominated strategy reduces matrix size without altering the overall value of the game or changing the set of optimal strategies[cite: 1].",
        "expected_source": "CSE281_Lecture 5.pdf"
    },
    {
        "question": "What steps should be followed to solve a 2x2 zero-sum matrix game?",
        "reference": "First, test the matrix for a saddle point. If no saddle point exists, solve for the optimal mixed strategies by setting up an equation that equalizes expected payoffs across opponent moves[cite: 1].",
        "expected_source": "CSE281_Lecture 5.pdf"
    }
]