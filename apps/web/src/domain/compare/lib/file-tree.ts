export type FileNode = {
  path: string;
  name: string;
  type: "file" | "directory";
  extension?: string;
  children?: FileNode[];
};

export type FileTreeData = FileNode[];

export function buildFileTree(paths: string[]): FileTreeData {
  const root: FileNode[] = [];
  const nodeMap = new Map<string, FileNode>();

  for (const path of [...paths].sort()) {
    const parts = path.split("/").filter(Boolean);
    let currentPath = "";
    let currentLevel = root;

    parts.forEach((part, index) => {
      const isLast = index === parts.length - 1;
      currentPath = currentPath ? `${currentPath}/${part}` : part;

      if (!nodeMap.has(currentPath)) {
        const node: FileNode = {
          path: currentPath,
          name: part,
          type: isLast ? "file" : "directory",
          extension: isLast ? getFileExtension(part) : undefined,
          children: isLast ? undefined : [],
        };
        nodeMap.set(currentPath, node);
        currentLevel.push(node);
      }

      const node = nodeMap.get(currentPath);
      if (node?.children) {
        currentLevel = node.children;
      }
    });
  }

  return root;
}

export function collectDirectoryPaths(tree: FileTreeData): string[] {
  const paths: string[] = [];

  const visit = (nodes: FileNode[]) => {
    for (const node of nodes) {
      if (node.type === "directory") {
        paths.push(node.path);
        if (node.children) {
          visit(node.children);
        }
      }
    }
  };

  visit(tree);
  return paths;
}

export function collectDirectoryPathsInSubtree(node: FileNode): string[] {
  if (node.type !== "directory") {
    return [];
  }

  return [node.path, ...collectDirectoryPaths(node.children ?? [])];
}

export function flattenTree(tree: FileTreeData): string[] {
  const paths: string[] = [];

  const traverse = (nodes: FileNode[]) => {
    nodes.forEach((node) => {
      if (node.type === "file") {
        paths.push(node.path);
      }
      if (node.children) {
        traverse(node.children);
      }
    });
  };

  traverse(tree);
  return paths;
}

export function findNodeByPath(tree: FileTreeData, path: string): FileNode | null {
  for (const node of tree) {
    if (node.path === path) {
      return node;
    }
    if (node.children) {
      const found = findNodeByPath(node.children, path);
      if (found) {
        return found;
      }
    }
  }
  return null;
}

export function getLanguageFromExtension(extension?: string): string {
  if (!extension) {
    return "text";
  }

  const languageMap: Record<string, string> = {
    js: "javascript",
    jsx: "javascript",
    ts: "typescript",
    tsx: "typescript",
    py: "python",
    rb: "ruby",
    go: "go",
    rs: "rust",
    java: "java",
    cpp: "cpp",
    c: "c",
    cs: "csharp",
    php: "php",
    swift: "swift",
    kt: "kotlin",
    sql: "sql",
    sh: "bash",
    bash: "bash",
    yml: "yaml",
    yaml: "yaml",
    json: "json",
    xml: "xml",
    html: "html",
    css: "css",
    scss: "scss",
    sass: "sass",
    less: "less",
    md: "markdown",
    txt: "text",
  };

  return languageMap[extension.toLowerCase()] ?? "text";
}

export function getFileIconColor(extension?: string): string {
  if (!extension) {
    return "text-muted-foreground";
  }
  const colors: Record<string, string> = {
    js: "text-yellow-500",
    jsx: "text-yellow-500",
    ts: "text-blue-500",
    tsx: "text-blue-500",
    py: "text-blue-400",
    json: "text-yellow-600",
    html: "text-orange-500",
    css: "text-blue-400",
    md: "text-gray-400",
    yml: "text-red-400",
    yaml: "text-red-400",
  };
  return colors[extension.toLowerCase()] ?? "text-muted-foreground";
}

function getFileExtension(filename: string): string | undefined {
  return filename.match(/\.([^.]+)$/)?.[1];
}
