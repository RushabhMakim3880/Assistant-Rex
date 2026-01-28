
export enum LogType {
  SYSTEM = 'SYS_INIT',
  NEURAL = 'NEURAL_V',
  ERROR = 'ERROR_X',
  USER = 'USER_IO'
}

export interface NeuralLogItem {
  id: number;
  type: LogType;
  message: string;
  timestamp: string;
  isAi: boolean;
}

export interface SystemStats {
  flow: string;
  temp: string;
  cohesion: string;
  time: string;
}
