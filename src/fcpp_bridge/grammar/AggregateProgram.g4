// FCPP Aggregate Program Grammar — Phase 6
//
// Generate Python parser stubs (regenerate after any grammar change):
//   java -jar antlr-4.13.1-complete.jar \
//       -Dlanguage=Python3 \
//       -o src/fcpp_bridge/grammar/__antlr_gen \
//       src/fcpp_bridge/grammar/AggregateProgram.g4
//
// Install ANTLR Python runtime:
//   pip install antlr4-python3-runtime==4.13.1
//
// Phase 6 additions: if/elif/else, while, for-range, switch/case, assignments.
// These mirror the Python DSL constructs that the Python-AST transpiler handles;
// if you write aggregate functions as Python classes you don't need this grammar
// directly — it is used only by the text-mode ANTLR parser.

grammar AggregateProgram;

// ─── Parser Rules ────────────────────────────────────────────────────────────

aggregateProgram
    : functionDef+ EOF
    ;

functionDef
    : DEF NAME COLON
      initialStateDef
      computeDef
    ;

initialStateDef
    : INITIAL_STATE COLON expr
    ;

computeDef
    : COMPUTE LPAREN NAME COMMA NAME RPAREN COLON stmt+
    ;

// ── Statements ────────────────────────────────────────────────────────────────

stmt
    : ifStmt        # IfStatement
    | whileStmt     # WhileStatement
    | forStmt       # ForStatement
    | switchStmt    # SwitchStatement
    | assignStmt    # AssignStatement
    | returnStmt    # ReturnStatement
    | expr SEMI?    # ExprStatement
    ;

ifStmt
    : IF LPAREN expr RPAREN LBRACE stmt* RBRACE
      (ELSE IF LPAREN expr RPAREN LBRACE stmt* RBRACE)*
      (ELSE LBRACE stmt* RBRACE)?
    ;

whileStmt
    : WHILE LPAREN expr RPAREN LBRACE stmt* RBRACE
    ;

forStmt
    : FOR LPAREN NAME IN RANGE LPAREN argList RPAREN RPAREN LBRACE stmt* RBRACE
    ;

switchStmt
    : SWITCH LPAREN expr RPAREN LBRACE caseClause* defaultClause? RBRACE
    ;

caseClause
    : CASE atom COLON stmt*
    ;

defaultClause
    : DEFAULT COLON stmt*
    ;

assignStmt
    : NAME ASSIGN expr SEMI?
    ;

returnStmt
    : RETURN expr SEMI?
    ;

// ── Expressions ───────────────────────────────────────────────────────────────

expr
    : expr op=(PLUS | MINUS | STAR | SLASH | PERCENT) expr   # BinaryExpr
    | expr op=(EQ | NEQ | LT | GT | LTE | GTE) expr         # CompareExpr
    | expr op=(AND | OR) expr                                # BoolExpr
    | NOT expr                                               # NotExpr
    | expr IF expr ELSE expr                                 # TernaryExpr
    | primitiveCall                                           # PrimCall
    | functionCall                                           # FuncCall
    | atom                                                   # AtomExpr
    | LPAREN expr RPAREN                                     # ParenExpr
    ;

primitiveCall
    : primitive LPAREN argList? RPAREN
    ;

functionCall
    : NAME LPAREN argList? RPAREN
    ;

argList
    : expr (COMMA expr)*
    ;

atom
    : INT_LIT    # IntLiteral
    | FLOAT_LIT  # FloatLiteral
    | STRING_LIT # StringLiteral
    | NAME       # NameRef
    ;

primitive
    // basics.hpp
    : NBR | OLD | NBR_UID | OLDNBR | ALIGN | ALIGN_INPLACE | MOD_OTHER | SPLIT
    | FOLD_HOOD | COUNT_HOOD | SPAWN
    // utils.hpp
    | MIN_HOOD | MAX_HOOD | SUM_HOOD | MEAN_HOOD | ALL_HOOD | ANY_HOOD | LIST_HOOD
    // spreading.hpp
    | ABF_DISTANCE | ABF_HOPS | BIS_DISTANCE | FLEX_DISTANCE
    | BROADCAST | BIS_KSOURCE_BROADCAST
    // collection.hpp
    | GOSSIP | GOSSIP_MIN | GOSSIP_MAX | GOSSIP_MEAN
    | SP_COLLECTION | MP_COLLECTION | WMP_COLLECTION
    | LIST_IDEM_COLLECTION | LIST_ARITH_COLLECTION
    // geometry.hpp
    | FOLLOW_TARGET | FOLLOW_PATH | FOLLOW_TRACK
    | RANDOM_RECTANGLE_TARGET | RECTANGLE_WALK
    | NEIGHBOUR_ELASTIC_FORCE | NEIGHBOUR_GRAVITATIONAL_FORCE | NEIGHBOUR_CHARGED_FORCE
    | LINE_ELASTIC_FORCE | PLANE_ELASTIC_FORCE
    | POINT_ELASTIC_FORCE | POINT_GRAVITATIONAL_FORCE
    // election.hpp
    | DIAMETER_ELECTION | DIAMETER_ELECTION_DISTANCE
    | COLOR_ELECTION | COLOR_ELECTION_DISTANCE
    | WAVE_ELECTION | WAVE_ELECTION_DISTANCE
    // time.hpp
    | CONSTANT | CONSTANT_AFTER | COUNTER | DELAY
    | ROUND_SINCE | TIME_SINCE | TIMED_DECAY | EXPONENTIAL_FILTER
    | SHARED_CLOCK | SHARED_DECAY | SHARED_FILTER
    | TOGGLE | TOGGLE_FILTER
    ;

// ─── Lexer Rules ─────────────────────────────────────────────────────────────

// Keywords
DEF           : 'def' ;
INITIAL_STATE : 'initial_state' ;
COMPUTE       : 'compute' ;
IF            : 'if' ;
ELSE          : 'else' ;
WHILE         : 'while' ;
FOR           : 'for' ;
IN            : 'in' ;
RANGE         : 'range' ;
SWITCH        : 'switch' ;
CASE          : 'case' ;
DEFAULT       : 'default' ;
BREAK         : 'break' ;
RETURN        : 'return' ;
NOT           : 'not' ;
AND           : 'and' ;
OR            : 'or' ;
ASSIGN        : '=' ;

// FCPP primitives — neighbourhood & temporal
NBR           : 'nbr' ;
OLD           : 'old' ;
MAX_HOOD      : 'max_hood' ;
MIN_HOOD      : 'min_hood' ;
FOLD_HOOD     : 'fold_hood' ;
COUNT_HOOD    : 'count_hood' ;

// FCPP primitives — spreading & collection
SPAWN          : 'spawn' ;
BROADCAST      : 'broadcast' ;
GOSSIP         : 'gossip' ;
SP_COLLECTION  : 'sp_collection' ;
MP_COLLECTION  : 'mp_collection' ;
WMP_COLLECTION : 'wmp_collection' ;
BIS_DISTANCE   : 'bis_distance' ;
ABF_DISTANCE   : 'abf_distance' ;

// FCPP primitives — geometry & movement
RECTANGLE_WALK              : 'rectangle_walk' ;
FOLLOW_TARGET               : 'follow_target' ;
FOLLOW_PATH                 : 'follow_path' ;
FOLLOW_TRACK                : 'follow_track' ;
RANDOM_RECTANGLE_TARGET     : 'random_rectangle_target' ;
NEIGHBOUR_ELASTIC_FORCE     : 'neighbour_elastic_force' ;
NEIGHBOUR_GRAVITATIONAL_FORCE : 'neighbour_gravitational_force' ;
NEIGHBOUR_CHARGED_FORCE     : 'neighbour_charged_force' ;
LINE_ELASTIC_FORCE          : 'line_elastic_force' ;
PLANE_ELASTIC_FORCE         : 'plane_elastic_force' ;
POINT_ELASTIC_FORCE         : 'point_elastic_force' ;
POINT_GRAVITATIONAL_FORCE   : 'point_gravitational_force' ;

// FCPP primitives — basics.hpp additions
NBR_UID       : 'nbr_uid' ;
OLDNBR        : 'oldnbr' ;
ALIGN         : 'align' ;
ALIGN_INPLACE : 'align_inplace' ;
MOD_OTHER     : 'mod_other' ;
SPLIT         : 'split' ;

// FCPP primitives — utils.hpp additions
SUM_HOOD  : 'sum_hood' ;
MEAN_HOOD : 'mean_hood' ;
ALL_HOOD  : 'all_hood' ;
ANY_HOOD  : 'any_hood' ;
LIST_HOOD : 'list_hood' ;

// FCPP primitives — spreading.hpp additions
ABF_HOPS              : 'abf_hops' ;
FLEX_DISTANCE         : 'flex_distance' ;
BIS_KSOURCE_BROADCAST : 'bis_ksource_broadcast' ;

// FCPP primitives — collection.hpp additions
GOSSIP_MIN            : 'gossip_min' ;
GOSSIP_MAX            : 'gossip_max' ;
GOSSIP_MEAN           : 'gossip_mean' ;
LIST_IDEM_COLLECTION  : 'list_idem_collection' ;
LIST_ARITH_COLLECTION : 'list_arith_collection' ;

// FCPP primitives — election.hpp
DIAMETER_ELECTION          : 'diameter_election' ;
DIAMETER_ELECTION_DISTANCE : 'diameter_election_distance' ;
COLOR_ELECTION             : 'color_election' ;
COLOR_ELECTION_DISTANCE    : 'color_election_distance' ;
WAVE_ELECTION              : 'wave_election' ;
WAVE_ELECTION_DISTANCE     : 'wave_election_distance' ;

// FCPP primitives — time.hpp
CONSTANT          : 'constant' ;
CONSTANT_AFTER    : 'constant_after' ;
COUNTER           : 'counter' ;
DELAY             : 'delay' ;
ROUND_SINCE       : 'round_since' ;
TIME_SINCE        : 'time_since' ;
TIMED_DECAY       : 'timed_decay' ;
EXPONENTIAL_FILTER : 'exponential_filter' ;
SHARED_CLOCK      : 'shared_clock' ;
SHARED_DECAY      : 'shared_decay' ;
SHARED_FILTER     : 'shared_filter' ;
TOGGLE            : 'toggle' ;
TOGGLE_FILTER     : 'toggle_filter' ;

// Operators
PLUS    : '+' ;
MINUS   : '-' ;
STAR    : '*' ;
SLASH   : '/' ;
PERCENT : '%' ;
EQ      : '==' ;
NEQ     : '!=' ;
LTE     : '<=' ;
GTE     : '>=' ;
LT      : '<' ;
GT      : '>' ;

// Punctuation
LPAREN : '(' ;
RPAREN : ')' ;
LBRACE : '{' ;
RBRACE : '}' ;
LBRACKET : '[' ;
RBRACKET : ']' ;
COMMA  : ',' ;
COLON  : ':' ;
SEMI   : ';' ;
DOT    : '.' ;

// Literals
INT_LIT   : [0-9]+ ;
FLOAT_LIT : [0-9]+ '.' [0-9]* | '.' [0-9]+ ;
STRING_LIT: '"' (~["\r\n])* '"' | '\'' (~['\r\n])* '\'' ;

// Identifiers
NAME : [a-zA-Z_] [a-zA-Z_0-9]* ;

// Skip whitespace and comments
WS      : [ \t\r\n]+ -> skip ;
COMMENT : '#' ~[\r\n]* -> skip ;
