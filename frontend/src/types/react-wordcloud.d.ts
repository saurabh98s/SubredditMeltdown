declare module 'react-wordcloud' {
  export interface WordCloudWord {
    text: string;
    value: number;
    [key: string]: any;
  }

  export interface WordCloudCallbacks {
    getWordColor?: (word: WordCloudWord) => string;
    getWordTooltip?: (word: WordCloudWord) => string;
    onWordClick?: (word: WordCloudWord, event?: React.MouseEvent) => void;
    onWordMouseOut?: (word: WordCloudWord, event?: React.MouseEvent) => void;
    onWordMouseOver?: (word: WordCloudWord, event?: React.MouseEvent) => void;
  }

  export interface WordCloudOptions {
    colors?: string[];
    deterministic?: boolean;
    enableTooltip?: boolean;
    fontFamily?: string;
    fontSizes?: [number, number];
    fontStyle?: string;
    fontWeight?: string | number;
    padding?: number;
    rotations?: number;
    rotationAngles?: [number, number];
    scale?: string;
    spiral?: string;
    transitionDuration?: number;
  }

  export interface MinMaxPair {
    min: number;
    max: number;
  }

  export interface Scale {
    linear: () => any;
    log: () => any;
    sqrt: () => any;
  }

  export interface SpiralType {
    archimedean: () => any;
    rectangular: () => any;
  }

  export interface Props {
    callbacks?: WordCloudCallbacks;
    maxWords?: number;
    minSize?: [number, number];
    options?: WordCloudOptions;
    size?: [number, number];
    words: WordCloudWord[];
  }

  const ReactWordCloud: React.FC<Props>;
  export default ReactWordCloud;
} 