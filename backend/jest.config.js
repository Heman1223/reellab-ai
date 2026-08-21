/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  moduleNameMapper: {
    '^@shared/(.*)$': '<rootDir>/../shared/$1',
  },
  // Tests must never reach a real database or a real AI service.
  setupFiles: ['<rootDir>/tests/setup.ts'],
  testTimeout: 15000,
};
