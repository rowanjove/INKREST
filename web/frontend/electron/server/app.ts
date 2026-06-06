import express from 'express';
import cors from 'cors';
import { createServer as createHttpServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import { chaptersRouter } from './routes/chapters';
import { stateRouter } from './routes/state';
import { assetsRouter } from './routes/assets';
import { configRouter } from './routes/config';
import { exportRouter } from './routes/export';

let io: SocketIOServer;

export function getIO(): SocketIOServer {
  return io;
}

export async function createServer(port: number = 3001) {
  const app = express();

  app.use(cors());
  app.use(express.json({ limit: '10mb' }));

  // API routes
  app.use('/api/chapters', chaptersRouter);
  app.use('/api/state', stateRouter);
  app.use('/api/assets', assetsRouter);
  app.use('/api/config', configRouter);
  app.use('/api/export', exportRouter);

  app.get('/api/health', (_req, res) => {
    res.json({ status: 'ok' });
  });

  // HTTP + Socket.IO
  const httpServer = createHttpServer(app);
  io = new SocketIOServer(httpServer, {
    cors: { origin: '*' },
  });

  io.on('connection', (socket) => {
    console.log('Client connected:', socket.id);
    socket.on('disconnect', () => {
      console.log('Client disconnected:', socket.id);
    });
  });

  return new Promise<any>((resolve) => {
    const server = httpServer.listen(port, () => {
      console.log(`Express server running on port ${port}`);
      resolve(server);
    });
  });
}
