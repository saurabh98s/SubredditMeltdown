declare module 'd3-cloud' {
  export interface Word {
    text: string;
    size: number;
    [propName: string]: any;
  }

  export interface Cloud {
    start: () => void;
    stop: () => void;
    timeInterval: (interval: number) => Cloud;
    words: (words: Word[]) => Cloud;
    size: (size: [number, number]) => Cloud;
    font: (font: string | ((word: Word) => string)) => Cloud;
    fontStyle: (style: string | ((word: Word) => string)) => Cloud;
    fontWeight: (weight: string | ((word: Word) => string)) => Cloud;
    rotate: (rotate: number | ((word: Word) => number)) => Cloud;
    text: (text: (word: Word) => string) => Cloud;
    spiral: (spiral: string | ((size: number) => (t: number) => [number, number])) => Cloud;
    fontSize: (size: number | ((word: Word) => number)) => Cloud;
    padding: (padding: number | ((word: Word) => number)) => Cloud;
    random: (random: () => number) => Cloud;
    canvas: (canvas: () => void) => Cloud;
    on: (type: string, listener: (word: Word) => void) => Cloud;
  }

  export default function(): Cloud;
} 