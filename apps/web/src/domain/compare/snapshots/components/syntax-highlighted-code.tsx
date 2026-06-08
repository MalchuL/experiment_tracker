import { cn } from "@/lib/utils";

type TokenType =
  | "plain"
  | "comment"
  | "keyword"
  | "string"
  | "number"
  | "function"
  | "type"
  | "property"
  | "operator"
  | "punctuation";

type SyntaxToken = {
  type: TokenType;
  content: string;
};

interface SyntaxHighlightedCodeProps {
  content: string;
  language?: string;
  className?: string;
}

const TOKEN_CLASS_BY_TYPE: Record<TokenType, string> = {
  plain: "",
  comment: "text-muted-foreground italic",
  keyword: "text-blue-700 dark:text-blue-300",
  string: "text-emerald-700 dark:text-emerald-300",
  number: "text-orange-700 dark:text-orange-300",
  function: "text-violet-700 dark:text-violet-300",
  type: "text-cyan-700 dark:text-cyan-300",
  property: "text-rose-700 dark:text-rose-300",
  operator: "text-muted-foreground",
  punctuation: "text-muted-foreground/80",
};

const LANGUAGE_ALIASES: Record<string, string> = {
  bash: "shell",
  c: "cpp",
  csharp: "cpp",
  h: "cpp",
  hpp: "cpp",
  html: "markup",
  javascript: "typescript",
  jsx: "typescript",
  less: "css",
  md: "markdown",
  py: "python",
  rb: "ruby",
  sass: "css",
  scss: "css",
  sh: "shell",
  ts: "typescript",
  tsx: "typescript",
  xml: "markup",
  yml: "yaml",
};

const KEYWORDS_BY_LANGUAGE: Record<string, Set<string>> = {
  cpp: new Set([
    "alignas",
    "alignof",
    "auto",
    "bool",
    "break",
    "case",
    "catch",
    "char",
    "class",
    "const",
    "constexpr",
    "continue",
    "default",
    "delete",
    "do",
    "double",
    "else",
    "enum",
    "explicit",
    "export",
    "extern",
    "false",
    "float",
    "for",
    "friend",
    "if",
    "inline",
    "int",
    "long",
    "namespace",
    "new",
    "nullptr",
    "operator",
    "private",
    "protected",
    "public",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "template",
    "this",
    "throw",
    "true",
    "try",
    "typedef",
    "typename",
    "union",
    "unsigned",
    "using",
    "virtual",
    "void",
    "volatile",
    "while",
  ]),
  css: new Set([
    "and",
    "from",
    "important",
    "in",
    "not",
    "only",
    "or",
    "to",
  ]),
  go: new Set([
    "break",
    "case",
    "chan",
    "const",
    "continue",
    "default",
    "defer",
    "else",
    "fallthrough",
    "for",
    "func",
    "go",
    "goto",
    "if",
    "import",
    "interface",
    "map",
    "package",
    "range",
    "return",
    "select",
    "struct",
    "switch",
    "type",
    "var",
  ]),
  java: new Set([
    "abstract",
    "boolean",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extends",
    "false",
    "final",
    "finally",
    "float",
    "for",
    "if",
    "implements",
    "import",
    "instanceof",
    "int",
    "interface",
    "long",
    "new",
    "null",
    "package",
    "private",
    "protected",
    "public",
    "return",
    "short",
    "static",
    "super",
    "switch",
    "this",
    "throw",
    "throws",
    "true",
    "try",
    "void",
    "while",
  ]),
  json: new Set(["false", "null", "true"]),
  python: new Set([
    "False",
    "None",
    "True",
    "and",
    "as",
    "assert",
    "async",
    "await",
    "break",
    "class",
    "continue",
    "def",
    "del",
    "elif",
    "else",
    "except",
    "finally",
    "for",
    "from",
    "global",
    "if",
    "import",
    "in",
    "is",
    "lambda",
    "nonlocal",
    "not",
    "or",
    "pass",
    "raise",
    "return",
    "try",
    "while",
    "with",
    "yield",
  ]),
  ruby: new Set([
    "BEGIN",
    "END",
    "alias",
    "and",
    "begin",
    "break",
    "case",
    "class",
    "def",
    "defined?",
    "do",
    "else",
    "elsif",
    "end",
    "ensure",
    "false",
    "for",
    "if",
    "in",
    "module",
    "next",
    "nil",
    "not",
    "or",
    "redo",
    "rescue",
    "retry",
    "return",
    "self",
    "super",
    "then",
    "true",
    "undef",
    "unless",
    "until",
    "when",
    "while",
    "yield",
  ]),
  rust: new Set([
    "as",
    "async",
    "await",
    "break",
    "const",
    "continue",
    "crate",
    "dyn",
    "else",
    "enum",
    "extern",
    "false",
    "fn",
    "for",
    "if",
    "impl",
    "in",
    "let",
    "loop",
    "match",
    "mod",
    "move",
    "mut",
    "pub",
    "ref",
    "return",
    "self",
    "Self",
    "static",
    "struct",
    "super",
    "trait",
    "true",
    "type",
    "unsafe",
    "use",
    "where",
    "while",
  ]),
  shell: new Set([
    "case",
    "do",
    "done",
    "elif",
    "else",
    "esac",
    "export",
    "fi",
    "for",
    "function",
    "if",
    "in",
    "local",
    "then",
    "while",
  ]),
  sql: new Set([
    "ALTER",
    "AND",
    "AS",
    "ASC",
    "BY",
    "CREATE",
    "DELETE",
    "DESC",
    "DROP",
    "FROM",
    "GROUP",
    "HAVING",
    "IN",
    "INSERT",
    "INTO",
    "JOIN",
    "LEFT",
    "LIMIT",
    "NOT",
    "NULL",
    "ON",
    "OR",
    "ORDER",
    "RIGHT",
    "SELECT",
    "SET",
    "TABLE",
    "UPDATE",
    "VALUES",
    "WHERE",
  ]),
  typescript: new Set([
    "abstract",
    "as",
    "async",
    "await",
    "boolean",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "debugger",
    "declare",
    "default",
    "delete",
    "do",
    "else",
    "enum",
    "export",
    "extends",
    "false",
    "finally",
    "for",
    "from",
    "function",
    "if",
    "implements",
    "import",
    "in",
    "instanceof",
    "interface",
    "let",
    "new",
    "null",
    "number",
    "of",
    "private",
    "protected",
    "public",
    "readonly",
    "return",
    "static",
    "string",
    "super",
    "switch",
    "this",
    "throw",
    "true",
    "try",
    "type",
    "typeof",
    "undefined",
    "var",
    "void",
    "while",
    "yield",
  ]),
};

export function SyntaxHighlightedCode({
  content,
  language = "text",
  className,
}: SyntaxHighlightedCodeProps) {
  const tokens = tokenize(content || " ", normalizeLanguage(language));

  return (
    <span className={cn("whitespace-pre-wrap break-words", className)}>
      {tokens.map((token, index) => (
        <span key={`${index}-${token.content}`} className={TOKEN_CLASS_BY_TYPE[token.type]}>
          {token.content}
        </span>
      ))}
    </span>
  );
}

function normalizeLanguage(language?: string) {
  if (!language) {
    return "text";
  }

  const normalized = language.toLowerCase();
  return LANGUAGE_ALIASES[normalized] ?? normalized;
}

function tokenize(content: string, language: string): SyntaxToken[] {
  if (language === "text") {
    return [{ type: "plain", content }];
  }

  if (language === "markdown") {
    return tokenizeMarkdown(content);
  }

  if (language === "yaml") {
    return tokenizeYaml(content);
  }

  if (language === "markup") {
    return tokenizeMarkup(content);
  }

  return tokenizeCode(content, language);
}

function tokenizeMarkdown(content: string): SyntaxToken[] {
  if (/^\s{0,3}#{1,6}\s/.test(content)) {
    return [{ type: "keyword", content }];
  }
  return splitByPatterns(content, [
    { type: "comment", regex: /<!--.*?-->/ },
    { type: "string", regex: /`[^`]*`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)/ },
    { type: "keyword", regex: /^\s*[-*+]\s+/ },
  ]);
}

function tokenizeYaml(content: string): SyntaxToken[] {
  return splitByPatterns(content, [
    { type: "comment", regex: /#.*/ },
    { type: "property", regex: /^\s*[\w.-]+(?=\s*:)/ },
    { type: "string", regex: /"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/ },
    { type: "keyword", regex: /\b(?:false|null|true|yes|no|on|off)\b/i },
    { type: "number", regex: /\b-?\d+(?:\.\d+)?\b/ },
  ]);
}

function tokenizeMarkup(content: string): SyntaxToken[] {
  return splitByPatterns(content, [
    { type: "comment", regex: /<!--.*?-->/ },
    { type: "keyword", regex: /<\/?[A-Za-z][\w:-]*/ },
    { type: "property", regex: /\s[\w:-]+(?==)/ },
    { type: "string", regex: /"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/ },
    { type: "punctuation", regex: /\/?>/ },
  ]);
}

function tokenizeCode(content: string, language: string): SyntaxToken[] {
  const keywords = KEYWORDS_BY_LANGUAGE[language] ?? new Set<string>();

  return splitByPatterns(content, [
    { type: "comment", regex: commentRegex(language) },
    { type: "string", regex: stringRegex(language) },
    { type: "property", regex: propertyRegex(language) },
    { type: "number", regex: /\b(?:0x[\da-f]+|\d+(?:\.\d+)?(?:e[+-]?\d+)?)\b/i },
    { type: "function", regex: /\b[A-Za-z_$][\w$]*(?=\s*\()/ },
    { type: "type", regex: /\b[A-Z][A-Za-z0-9_]*\b/ },
    {
      type: "keyword",
      regex: /\b[A-Za-z_$][\w$]*\b/,
      classify: (value) => (keywords.has(value) || keywords.has(value.toUpperCase()) ? "keyword" : "plain"),
    },
    { type: "operator", regex: /[-+*/%=!<>|&?:~]+/ },
    { type: "punctuation", regex: /[()[\]{}.,;]/ },
  ]);
}

function commentRegex(language: string) {
  if (language === "python" || language === "ruby" || language === "shell") {
    return /#.*/;
  }
  if (language === "sql") {
    return /--.*|\/\*.*?\*\//;
  }
  if (language === "css") {
    return /\/\*.*?\*\//;
  }
  return /\/\/.*|\/\*.*?\*\//;
}

function stringRegex(language: string) {
  if (language === "python" || language === "ruby") {
    return /(?:[rubf]+)?("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')/i;
  }
  return /`(?:\\.|[^`\\])*`|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'/;
}

function propertyRegex(language: string) {
  if (language === "css") {
    return /(?:--[\w-]+|[A-Za-z-]+)(?=\s*:)/;
  }
  if (language === "json") {
    return /"(?:\\.|[^"\\])*"(?=\s*:)/;
  }
  return /\b[A-Za-z_$][\w$]*(?=\s*:)/;
}

function splitByPatterns(
  content: string,
  patterns: Array<{
    type: TokenType;
    regex: RegExp;
    classify?: (value: string) => TokenType;
  }>
): SyntaxToken[] {
  const tokens: SyntaxToken[] = [];
  let remaining = content;

  while (remaining.length > 0) {
    type PatternMatch = { index: number; value: string; type: TokenType; patternIndex: number };
    let bestMatch: PatternMatch | null = null;

    for (let patternIndex = 0; patternIndex < patterns.length; patternIndex += 1) {
      const pattern = patterns[patternIndex];
      const regex = new RegExp(pattern.regex.source, pattern.regex.flags);
      const match = regex.exec(remaining);
      if (!match?.[0]) {
        continue;
      }

      const candidate: PatternMatch = {
        index: match.index,
        value: match[0],
        type: pattern.classify?.(match[0]) ?? pattern.type,
        patternIndex,
      };
      if (
        !bestMatch ||
        candidate.index < bestMatch.index ||
        (candidate.index === bestMatch.index && candidate.patternIndex < bestMatch.patternIndex)
      ) {
        bestMatch = candidate;
      }
    }

    if (!bestMatch) {
      tokens.push({ type: "plain", content: remaining });
      break;
    }

    if (bestMatch.index > 0) {
      tokens.push({ type: "plain", content: remaining.slice(0, bestMatch.index) });
    }
    tokens.push({ type: bestMatch.type, content: bestMatch.value });
    remaining = remaining.slice(bestMatch.index + bestMatch.value.length);
  }

  return mergeAdjacentPlainTokens(tokens);
}

function mergeAdjacentPlainTokens(tokens: SyntaxToken[]) {
  const mergedTokens: SyntaxToken[] = [];
  tokens.forEach((token) => {
    const previousToken = mergedTokens[mergedTokens.length - 1];
    if (previousToken?.type === token.type) {
      previousToken.content += token.content;
      return;
    }
    mergedTokens.push({ ...token });
  });
  return mergedTokens;
}
