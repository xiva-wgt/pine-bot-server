# coding=utf-8
# see https://www.tradingview.com/wiki/Appendix_B._Pine_Script_v2_lexer_gramma://www.tradingview.com/wiki/Appendix_C._Pine_Script_v2_parser_grammar 

import ply.yacc as yacc
from lexer import tokens

import vm.node as vm

## helper
def make_list2 (p, cls):
    if len(p) == 2:
        return p[1]
    else:
        l = p[1]
        if not isinstance(l, cls):
            l = cls(p[1])
        l.append(p[3])
        return l

def make_binop (p):
    if len(p) == 2:
        return p[1]
    else:
        return vm.BinOpNode(p[2], p[1], p[3])


## grammer definition
def p_statement_list (p):
    '''statement_list :
                      | statement
                      | statement_list statement'''
    if len(p) == 1:
        p[0] == None
    elif len(p) == 2:
        p[0] = vm.Node(p[1])
    else:
        p[0] = p[1].append(p[2])

def p_statement (p):
    '''statement : fun_def_stmt
                 | expression_stmt
                 | loop_break_stmt
                 | loop_continue_stmt'''
    p[0] = p[1]

# simple statements
def p_loop_break_stmt (p):
    'loop_break_stmt : BREAK DELIM'
    raise NotImplementedError

def p_loop_continue_stmt (p):
    'loop_continue_stmt : CONTINUE DELIM'
    raise NotImplementedError

# expression statements
def p_expression_stmt (p):
    '''expression_stmt : simple_expression DELIM
                       | complex_expression
                       | var_def_stmt
                       | var_defs_stmt
                       | var_assign_stmt'''
    p[0] = p[1]

def p_var_assign_stmt (p):
    'var_assign_stmt : ID ASSIGN expression DELIM'
    p[0] = vm.VarAssignNode(p[1], p[3])

def p_var_def_stmt (p):
    'var_def_stmt : var_def DELIM'
    p[0] = p[1]

def p_var_def (p):
    'var_def : ID DEFINE expression'
    p[0] = vm.VarDefNode(p[1], p[3])

def p_var_defs_stmt (p):
    'var_defs_stmt : LSQBR id_list RSQBR DEFINE LSQBR simple_expr_list RSQBR DELIM'
    raise NotImplementedError

def p_id_list (p):
    '''id_list : ID
               | id_list COMMA ID'''
    p[0] = make_list2(p, vm.Node)

# expression
def p_expression (p):
    '''expression : simple_expression
                  | complex_expression'''
    p[0] = p[1]

# simple_expression
def p_simple_expr_list (p):
    '''simple_expr_list : simple_expression
                        | simple_expr_list COMMA simple_expression
                        | id_list
                        | id_list COMMA simple_expression'''
    #print(p[1])
    converted = False
    # Convert id_list to list of VarRefNode
    if isinstance(p[1], str):
        n = vm.Node(vm.VarRefNode(p[1]))
        converted = True
    elif len(p[1].children) > 0 and isinstance(p[1].children[0], str):
        n = vm.Node()
        for s in p[1].children:
            n.append(vm.VarRefNode(s))
        converted = True
    else:
        n = p[1]

    if len(p) == 2:
        if not converted:
            n = vm.Node(n)
    else:
        n.append(p[3])

    p[0] = n


# Actually ternary_expression
def p_simple_expression (p):
    '''simple_expression : or_expr
                         | or_expr COND simple_expression COND_ELSE simple_expression'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = vm.IfNode(p[1], p[3], p[5])

def p_or_expr (p):
    '''or_expr : and_expr
               | or_expr OR and_expr'''
    p[0] = make_list2(p, vm.OrNode)

def p_and_expr (p):
    '''and_expr : eq_expr
                | and_expr AND eq_expr'''
    p[0] = make_list2(p, vm.AndNode)

def p_eq_expr (p):
    '''eq_expr : cmp_expr
               | cmp_expr EQ cmp_expr
               | cmp_expr NEQ cmp_expr'''
    p[0] = make_binop(p)

def p_cmp_expr (p):
    '''cmp_expr : add_expr
                | add_expr GT add_expr
                | add_expr GE add_expr
                | add_expr LT add_expr
                | add_expr LE add_expr'''
    p[0] = make_binop(p)

def p_add_expr (p):
    '''add_expr : mul_expr
                | add_expr PLUS mul_expr
                | add_expr MINUS mul_expr'''
    p[0] = make_binop(p)

def p_mul_expr (p):
    '''mul_expr : unary_expr
                | mul_expr MUL unary_expr
                | mul_expr DIV unary_expr
                | mul_expr MOD unary_expr'''
    p[0] = make_binop(p)

precedence = (
    ('right', 'UPLUS', 'UMINUS'),            # Unary minus operator
)
def p_unary_expr (p):
    '''unary_expr : sqbr_expr
                  | NOT sqbr_expr
                  | PLUS sqbr_expr %prec UPLUS
                  | MINUS sqbr_expr %prec UMINUS'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = vm.UniOpNode(p[1], p[2])

def p_sqbr_expr (p):
    '''sqbr_expr : atom
                 | atom LSQBR simple_expression RSQBR'''
    p[0] = make_binop(p)

def p_atom (p):
    '''atom : fun_call
            | var_ref
            | literal
            | LPAR simple_expression RPAR'''
    p[0] = p[1]

def p_var_ref (p):
    'var_ref : ID'
    p[0] = vm.VarRefNode(p[1])

def p_fun_call (p):
    'fun_call : ID LPAR fun_arg_list RPAR'
    p[0] = vm.FunCallNode(p[1], p[3])

def p_fun_arg_list (p):
    '''fun_arg_list : simple_expr_list
                    | kw_arg_list
                    | simple_expr_list COMMA kw_arg_list
                    | id_list COMMA kw_arg_list'''  # FIXME
    if len(p) == 2:
        if isinstance(p[1], vm.KwArgsNode):
            p[0] = (None, p[1])
        else:
            p[0] = (p[1], None)
    else:
        # Convert id_list to list of VarRefNode
        if isinstance(p[1], str):
            n = vm.Node(vm.VarRefNode(p[1]))
        elif len(p[1].children) > 0 and isinstance(p[1].children[0], str):
            n = vm.Node()
            for s in p[1].children:
                n.append(vm.VarRefNode(s))
        else:
            n = p[1]
        p[0] = (n, p[3])

def p_kw_arg_list (p):
    '''kw_arg_list : kw_arg
                   | kw_arg_list COMMA kw_arg'''
    if len(p) == 2:
        d, kv = {}, p[1]
    else:
        d, kv = p[1], p[3]
    d[kv[0]] = kv[1]
    p[0] = d

def p_kw_arg (p):
    'kw_arg : ID DEFINE simple_expression'
    p[0] = (p[1], p[3])
    print(p[0])

def p_literal (p):
    '''literal : INT_LITERAL
               | FLOAT_LITERAL
               | STR_LITERAL
               | BOOL_LITERAL
               | COLOR_LITERAL'''
    p[0] = vm.LiteralNode(p[1])

# complex expression
def p_complex_expression (p):
    '''complex_expression : if_expr
                          | for_expr'''
    p[0] = p[1]

def p_if_expr (p):
    '''if_expr : IF_COND simple_expression stmts_block
               | IF_COND simple_expression stmts_block IF_COND_ELSE stmts_block'''
    if len(p) == 4:
        p[0] = vm.IfNode(p[2], p[3])
    else:
        p[0] = vm.IfNode(p[2], p[3], p[5])

def p_for_expr (p):
    '''for_expr : FOR_STMT var_def FOR_STMT_TO simple_expression stmts_block
                | FOR_STMT var_def FOR_STMT_TO simple_expression FOR_STMT_BY'''     # FIXME
    p[0] = vm.ForNode(p[2], p[4], p[5])

def p_stmts_block (p):
    'stmts_block : BEGIN statement_list END'
    p[0] = p[2]


# function definition
def p_fun_def_stmt (p):
    '''fun_def_stmt : fun_def_stmt_1
                    | fun_def_stmt_m'''
    p[0] = p[1]

def p_fun_def_stmt_1 (p):
    'fun_def_stmt_1 : ID LPAR id_list RPAR ARROW simple_expression DELIM'
    p[0] = vm.FunDefNode(p[1], p[3], p[6])

def p_fun_def_stmt_m (p):
    'fun_def_stmt_m : ID LPAR id_list RPAR ARROW stmts_block'
    p[0] = vm.FunDefNode(p[1], p[3], p[6])

# Error handling
def p_error (p):
    print(p)


from lexer import Lexer
def parse (data):
    parser = yacc.yacc()
    import logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    return parser.parse(data, lexer=Lexer(), debug=logger)


if __name__ == '__main__':
    import sys
    from preprocess import preprocess
    with open(sys.argv[1]) as f:
        data = preprocess(f.read())
        print(parse(data))
