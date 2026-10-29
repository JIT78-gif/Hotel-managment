const assert = require('assert');
const isValid = (t) => typeof t === 'string' && t.trim().length > 0;

assert.strictEqual(isValid("Test Task"), true);
assert.strictEqual(isValid("Clean room 204"), true);
assert.strictEqual(isValid("   "), false);
assert.strictEqual(isValid(42), false);
console.log("Tests Passed!");
