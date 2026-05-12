"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { flip, offset, shift, size } from "@floating-ui/react"
import { PluginKey } from "@tiptap/pm/state"

// --- Hooks ---
import { useFloatingElement } from "@/hooks/use-floating-element"
import { useMenuNavigation } from "@/hooks/use-menu-navigation"
import { useTiptapEditor } from "@/hooks/use-tiptap-editor"

// --- Tiptap Editor ---
import type { Range } from "@tiptap/react"

// --- Tiptap UI ---
import { Suggestion } from "@tiptap/suggestion"

// --- UI Primitives ---
import {
  SuggestionPluginKey,
  type SuggestionKeyDownProps,
  type SuggestionProps,
} from "@tiptap/suggestion"

import { calculateStartPosition } from "@/components/tiptap-ui-utils/suggestion-menu/suggestion-menu-utils"
import type {
  SuggestionItem,
  SuggestionMenuProps,
} from "@/components/tiptap-ui-utils/suggestion-menu/suggestion-menu-types"

/**
 * A component that renders a suggestion menu for Tiptap editors.
 * Displays a floating menu when a trigger character is typed.
 */
export const SuggestionMenu = ({
  editor: providedEditor,
  floatingOptions,
  selector = "tiptap-suggestion-menu",
  children,
  maxHeight = 384,
  pluginKey = SuggestionPluginKey,
  ...internalSuggestionProps
}: SuggestionMenuProps) => {
  const { editor } = useTiptapEditor(providedEditor)

  const [show, setShow] = useState<boolean>(false)

  // If later we want the floating stick to the position while browser is scrolling,
  // we can uncomment this part and pass the getBoundingClientRect prop to FloatingElement instead of referenceElement.
  // const [internalClientRect, setInternalClientRect] = useState<DOMRect | null>(
  //   null
  // )
  const [internalDecorationNode, setInternalDecorationNode] =
    useState<HTMLElement | null>(null)
  const [internalCommand, setInternalCommand] = useState<
    ((item: SuggestionItem) => void) | null
  >(null)
  const [internalItems, setInternalItems] = useState<SuggestionItem[]>([])
  const [internalQuery, setInternalQuery] = useState<string>("")
  const [, setInternalRange] = useState<Range | null>(null)

  const { ref, style, getFloatingProps, isMounted } = useFloatingElement(
    show,
    internalDecorationNode,
    1000,
    {
      placement: "bottom-start",
      middleware: [
        offset(10),
        flip({
          mainAxis: true,
          crossAxis: false,
        }),
        shift(),
        size({
          apply({ availableHeight, elements }) {
            if (elements.floating) {
              const maxHeightValue = maxHeight
                ? Math.min(maxHeight, availableHeight)
                : availableHeight

              elements.floating.style.setProperty(
                "--suggestion-menu-max-height",
                `${maxHeightValue}px`
              )
            }
          },
        }),
      ],
      onOpenChange(open) {
        if (!open) {
          setShow(false)
        }
      },
      ...floatingOptions,
    }
  )

  const internalSuggestionPropsRef = useRef(internalSuggestionProps)

  useEffect(() => {
    internalSuggestionPropsRef.current = internalSuggestionProps
  }, [internalSuggestionProps])

  const closePopup = useCallback(() => {
    setShow(false)
  }, [])

  useEffect(() => {
    if (!editor || editor.isDestroyed) {
      return
    }

    const existingPlugin = editor.state.plugins.find(
      (plugin) => plugin.spec.key === pluginKey
    )
    if (existingPlugin) {
      editor.unregisterPlugin(pluginKey)
    }

    // Find the Mention extension that matches our trigger character (e.g. "@") so we can
    // pull suggestion configuration from it (e.g. allowSpaces, allowedPrefixes, startOfLine).
    const ourChar = internalSuggestionPropsRef.current.char ?? "@"

    const mentionExtension = editor.extensionManager.extensions.find((ext) => {
      if (ext.name !== "mention") return false

      const suggestions = ext.options?.suggestions
      if (suggestions?.length) {
        return suggestions.some(
          (s: Record<string, unknown>) => (s.char ?? "@") === ourChar
        )
      }

      return (ext.options?.suggestion?.char ?? "@") === ourChar
    })

    // We want to allow passing mention suggestion configuration either
    // via the main suggestion prop or via the suggestions array (for multiple trigger characters).
    // To support both, we pull out any relevant config from the Mention extension and pass it to the Suggestion plugin.
    // We also make sure to not override any props that are already passed directly to the SuggestionMenu component.
    const mentionSuggestionDefaults: Record<string, unknown> = {}

    if (mentionExtension) {
      let matchingConfig: Record<string, unknown> | null = null

      const suggestions = mentionExtension.options?.suggestions
      if (suggestions?.length) {
        matchingConfig = suggestions.find(
          (s: Record<string, unknown>) => (s.char ?? "@") === ourChar
        )
      } else if (mentionExtension.options?.suggestion) {
        matchingConfig = mentionExtension.options.suggestion
      }

      if (matchingConfig) {
        const managedKeys = new Set([
          "pluginKey",
          "editor",
          "render",
          "command",
          "items",
          "allow",
          "char",
        ])

        for (const key of Object.keys(matchingConfig)) {
          if (!managedKeys.has(key)) {
            mentionSuggestionDefaults[key] = matchingConfig[key]
          }
        }
      }
    }

    const suggestion = Suggestion({
      ...mentionSuggestionDefaults,
      pluginKey:
        pluginKey instanceof PluginKey ? pluginKey : new PluginKey(pluginKey),
      editor,

      allow(props) {
        const $from = editor.state.doc.resolve(props.range.from)

        // Check if we're inside an image node
        for (let depth = $from.depth; depth > 0; depth--) {
          if ($from.node(depth).type.name === "image") {
            return false // Don't allow slash command inside image (since we support captions)
          }
        }

        return true
      },

      command({ editor, range, props }) {
        if (!range) {
          return
        }

        const { view, state } = editor
        const { selection } = state

        const isMention = editor.extensionManager.extensions.some(
          (extension) => {
            if (extension.name !== "mention") return false

            const mentionSuggestions = extension.options?.suggestions
            if (mentionSuggestions?.length) {
              return mentionSuggestions.some(
                (s: Record<string, unknown>) =>
                  (s.char ?? "@") === internalSuggestionPropsRef.current.char
              )
            }

            return (
              (extension.options?.suggestion?.char ?? "@") ===
              internalSuggestionPropsRef.current.char
            )
          }
        )

        if (!isMention) {
          const cursorPosition = selection.$from.pos
          const previousNode = selection.$head?.nodeBefore

          const startPosition = previousNode
            ? calculateStartPosition(
                cursorPosition,
                previousNode,
                internalSuggestionPropsRef.current.char
              )
            : selection.$from.start()

          const transaction = state.tr.deleteRange(
            startPosition,
            cursorPosition
          )
          view.dispatch(transaction)
        }

        const rangeToUse = { ...range }

        const nodeAfter = view.state.selection.$to.nodeAfter
        const overrideSpace = nodeAfter?.text?.startsWith(" ")

        if (overrideSpace) {
          rangeToUse.to += 1
        }

        props.onSelect({ editor, range: rangeToUse, context: props.context })
      },

      render: () => {
        return {
          onStart: (props: SuggestionProps<SuggestionItem>) => {
            setInternalDecorationNode(
              (props.decorationNode as HTMLElement) ?? null
            )
            setInternalCommand(() => props.command)
            setInternalItems(props.items)
            setInternalQuery(props.query)
            setInternalRange(props.range)
            // setInternalClientRect(props.clientRect?.() ?? null)
            setShow(true)
          },

          onUpdate: (props: SuggestionProps<SuggestionItem>) => {
            setInternalDecorationNode(
              (props.decorationNode as HTMLElement) ?? null
            )
            setInternalCommand(() => props.command)
            setInternalItems(props.items)
            setInternalQuery(props.query)
            setInternalRange(props.range)
            // setInternalClientRect(props.clientRect?.() ?? null)
          },

          onKeyDown: (props: SuggestionKeyDownProps) => {
            if (props.event.key === "Escape") {
              closePopup()
              return true
            }
            return false
          },

          onExit: () => {
            setInternalDecorationNode(null)
            setInternalCommand(null)
            setInternalItems([])
            setInternalQuery("")
            setInternalRange(null)
            // setInternalClientRect(null)
            setShow(false)
          },
        }
      },
      ...internalSuggestionPropsRef.current,
    })

    editor.registerPlugin(suggestion)

    return () => {
      if (!editor.isDestroyed) {
        editor.unregisterPlugin(pluginKey)
      }
    }
  }, [editor, pluginKey, closePopup])

  const onSelect = useCallback(
    (item: SuggestionItem) => {
      closePopup()

      if (internalCommand) {
        internalCommand(item)
      }
    },
    [closePopup, internalCommand]
  )

  const { selectedIndex } = useMenuNavigation({
    editor: editor,
    query: internalQuery,
    items: internalItems,
    onSelect,
  })

  if (!isMounted || !show || !editor) {
    return null
  }

  return (
    <div
      ref={ref}
      style={style}
      {...getFloatingProps()}
      data-selector={selector}
      className="tiptap-suggestion-menu"
      role="listbox"
      aria-label="Suggestions"
      onPointerDown={(e) => e.preventDefault()}
    >
      {children({
        items: internalItems,
        selectedIndex,
        onSelect,
      })}
    </div>
  )
}
