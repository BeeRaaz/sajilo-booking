FROM node:24-slim

RUN corepack enable

WORKDIR /src

# Copy only dependencies files first
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

# Now copy the rest of the actual code
COPY . .

EXPOSE 3000

CMD ["pnpm", "dev"]
