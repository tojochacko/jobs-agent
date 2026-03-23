FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# --host binds to 0.0.0.0 so the port is reachable outside the container
CMD ["npm", "run", "dev", "--", "--host"]
