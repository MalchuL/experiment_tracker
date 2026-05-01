export type FileNode = {
  path: string;
  name: string;
  type: 'file' | 'directory';
  extension?: string;
  children?: FileNode[];
  content?: string;
};

export type FileTreeData = FileNode[];

/**
 * Parses an array of absolute file paths into a hierarchical tree structure
 * @param paths Array of absolute file paths with extensions
 * @returns Hierarchical tree structure
 */
export function buildFileTree(paths: string[]): FileTreeData {
  const root: FileNode[] = [];
  const nodeMap = new Map<string, FileNode>();

  // Sort paths to ensure parent directories are created first
  const sortedPaths = [...paths].sort();

  sortedPaths.forEach((path) => {
    const parts = path.split('/').filter(Boolean);
    let currentPath = '';
    let currentLevel = root;

    parts.forEach((part, index) => {
      const isLast = index === parts.length - 1;
      currentPath += '/' + part;

      if (!nodeMap.has(currentPath)) {
        const extension = isLast ? getFileExtension(part) : undefined;
        const node: FileNode = {
          path: currentPath,
          name: part,
          type: isLast ? 'file' : 'directory',
          extension,
          children: isLast ? undefined : [],
        };

        nodeMap.set(currentPath, node);
        currentLevel.push(node);
      }

      const node = nodeMap.get(currentPath)!;
      if (node.children) {
        currentLevel = node.children;
      }
    });
  });

  return root;
}

/**
 * Gets the file extension from a filename
 */
function getFileExtension(filename: string): string | undefined {
  const match = filename.match(/\.([^.]+)$/);
  return match ? match[1] : undefined;
}

/**
 * Flattens a file tree into a list of all file paths
 */
export function flattenTree(tree: FileTreeData): string[] {
  const paths: string[] = [];

  function traverse(nodes: FileNode[]) {
    nodes.forEach((node) => {
      if (node.type === 'file') {
        paths.push(node.path);
      }
      if (node.children) {
        traverse(node.children);
      }
    });
  }

  traverse(tree);
  return paths;
}

/**
 * Finds a node in the tree by path
 */
export function findNodeByPath(
  tree: FileTreeData,
  path: string
): FileNode | null {
  function search(nodes: FileNode[]): FileNode | null {
    for (const node of nodes) {
      if (node.path === path) {
        return node;
      }
      if (node.children) {
        const found = search(node.children);
        if (found) return found;
      }
    }
    return null;
  }

  return search(tree);
}

/**
 * Gets the language for syntax highlighting based on file extension
 */
export function getLanguageFromExtension(extension?: string): string {
  if (!extension) return 'text';

  const languageMap: Record<string, string> = {
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    py: 'python',
    rb: 'ruby',
    go: 'go',
    rs: 'rust',
    java: 'java',
    cpp: 'cpp',
    c: 'c',
    cs: 'csharp',
    php: 'php',
    swift: 'swift',
    kt: 'kotlin',
    sql: 'sql',
    sh: 'bash',
    bash: 'bash',
    yml: 'yaml',
    yaml: 'yaml',
    json: 'json',
    xml: 'xml',
    html: 'html',
    css: 'css',
    scss: 'scss',
    sass: 'sass',
    less: 'less',
    md: 'markdown',
    txt: 'text',
  };

  return languageMap[extension.toLowerCase()] || 'text';
}

/**
 * Gets icon color class based on file extension
 */
export function getFileIconColor(extension?: string): string {
  if (!extension) return 'text-muted-foreground';

  const colorMap: Record<string, string> = {
    js: 'text-yellow-500',
    jsx: 'text-yellow-500',
    ts: 'text-blue-500',
    tsx: 'text-blue-500',
    py: 'text-blue-400',
    json: 'text-yellow-600',
    html: 'text-orange-500',
    css: 'text-blue-400',
    md: 'text-gray-400',
    yml: 'text-red-400',
    yaml: 'text-red-400',
  };

  return colorMap[extension.toLowerCase()] || 'text-muted-foreground';
}
