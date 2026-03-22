FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

RUN npm list vite || echo "Vite not found"

EXPOSE 5173

CMD ["npm", "run", "dev"]