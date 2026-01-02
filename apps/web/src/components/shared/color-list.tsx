import { useState, useEffect, useMemo } from "react";
import ColorPicker from "../ui/color-picker";
import { Palette } from "lucide-react";

interface ColorListProps {
    currentColor: string;
    useColorPalette: boolean;
    onColorChange: (color: string) => void;
    colors: string[];
}

interface ColorOptionProps {
    color: string;
    setColor: (color: string) => void;
    onClick: () => void;
}

export function ColorList({ currentColor, useColorPalette, onColorChange, colors }: ColorListProps) {
    const isColorInList = useMemo(() => colors.includes(currentColor), [colors, currentColor]);
    return (
        <div className="flex gap-2 flex-wrap">
        {useColorPalette && (
            <ColorPicker
                value={currentColor}
                onChange={onColorChange}
            >
              <div
                className={`w-6 h-6 rounded-full border-2 transition-transform flex items-center justify-center ${
                    !isColorInList
                    ? "border-foreground scale-110"
                    : "border-transparent hover:scale-105"
                }`}
                style={{ backgroundColor: currentColor }}
                data-testid="color-picker"
                aria-label="Choose custom color"
              >
               <Palette className="w-4 h-4" />
              </div>
            </ColorPicker>
        )}
        {colors.map((color) => (
          <button
            key={color}
            type="button"
            className={`w-6 h-6 rounded-full border-2 transition-transform ${
                isColorInList && currentColor === color
                ? "border-foreground scale-110"
                : "border-transparent hover:scale-105"
            }`}
            style={{ backgroundColor: color }}
            onClick={() => {
                onColorChange(color);
            }}
            data-testid={`color-option-${color}`}
          />
        ))}
      </div>
    );
}