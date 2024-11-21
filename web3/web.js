"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __generator = (this && this.__generator) || function (thisArg, body) {
    var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
    return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
    function verb(n) { return function (v) { return step([n, v]); }; }
    function step(op) {
        if (f) throw new TypeError("Generator is already executing.");
        while (g && (g = 0, op[0] && (_ = 0)), _) try {
            if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
            if (y = 0, t) op = [op[0] & 2, t.value];
            switch (op[0]) {
                case 0: case 1: t = op; break;
                case 4: _.label++; return { value: op[1], done: false };
                case 5: _.label++; y = op[1]; op = [0]; continue;
                case 7: op = _.ops.pop(); _.trys.pop(); continue;
                default:
                    if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                    if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                    if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                    if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                    if (t[2]) _.ops.pop();
                    _.trys.pop(); continue;
            }
            op = body.call(thisArg, _);
        } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
        if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
    }
};
Object.defineProperty(exports, "__esModule", { value: true });
var express_1 = require("express");
var dotenv_1 = require("dotenv");
var thirdweb_1 = require("thirdweb");
var chains_1 = require("thirdweb/chains");
var wallets_1 = require("thirdweb/wallets");
var in_app_1 = require("thirdweb/wallets/in-app");
var wallet = (0, in_app_1.inAppWallet)();
(0, dotenv_1.config)();
var app = (0, express_1.default)();
app.use(express_1.default.json());
var PORT = process.env.PORT || 3000;
var chain = chains_1.polygonAmoy;
var client, contract;
var account;
// Initialize the contract
var initContract = function () { return __awaiter(void 0, void 0, void 0, function () {
    return __generator(this, function (_a) {
        if (!process.env.WALLET_PRIVATE_KEY || !process.env.THIRDWEB_SECRET_KEY) {
            throw new Error("No private key or THIRDWEB_SECRET_KEY found");
        }
        try {
            // Create a client using the secret key
            client = (0, thirdweb_1.createThirdwebClient)({
                secretKey: process.env.THIRDWEB_SECRET_KEY,
            });
            // Create an account using the private key
            account = (0, wallets_1.privateKeyToAccount)({
                client: client,
                privateKey: process.env.WALLET_PRIVATE_KEY,
            });
            // Get the contract instance
            contract = (0, thirdweb_1.getContract)({ client: client, chain: chain, address: "0xa4f81Da59D69BCe0663824543F3C0591516008aB" });
            console.log("Contract initialized at address: 0xa4f81Da59D69BCe0663824543F3C0591516008aB");
        }
        catch (err) {
            console.error("Error initializing contract: ", err);
            process.exit(1); // Exit process if contract initialization fails
        }
        return [2 /*return*/];
    });
}); };
// Define the async route handler
var storeGameResult = function (req, res) { return __awaiter(void 0, void 0, void 0, function () {
    var _a, player1, player2, score1, score2, winner, transaction, data, err_1;
    return __generator(this, function (_b) {
        switch (_b.label) {
            case 0:
                _b.trys.push([0, 2, , 3]);
                _a = req.body, player1 = _a.player1, player2 = _a.player2, score1 = _a.score1, score2 = _a.score2, winner = _a.winner;
                if (!player1 || !player2 || score1 === undefined || score2 === undefined || !winner) {
                    res.status(400).json({ error: "Invalid game result data" });
                    return [2 /*return*/];
                }
                transaction = (0, thirdweb_1.prepareContractCall)({
                    contract: contract,
                    method: "function storeGameResult(address _player1, address _player2, uint256 _score1, uint256 _score2, address _winner)",
                    params: [player1, player2, score1, score2, winner],
                });
                if (!transaction) {
                    res.status(500).json({ error: "Failed to prepare transaction" });
                    return [2 /*return*/];
                }
                return [4 /*yield*/, (0, thirdweb_1.sendAndConfirmTransaction)({
                        transaction: transaction,
                        account: account,
                    })];
            case 1:
                data = _b.sent();
                if (!data.transactionHash) {
                    res.status(500).json({ error: "Failed to store game result" });
                    return [2 /*return*/];
                }
                console.log("Game result stored on blockchain!");
                res.json({
                    message: "Game result stored successfully",
                    transactionHash: data.transactionHash,
                });
                return [3 /*break*/, 3];
            case 2:
                err_1 = _b.sent();
                console.error("Error storing game result: ", err_1);
                res.status(500).json({ error: "Failed to store game result" });
                return [3 /*break*/, 3];
            case 3: return [2 /*return*/];
        }
    });
}); };
// Set up the endpoint to store game results
app.post('/store_results', storeGameResult);
// Initialize the contract and start the server
initContract().then(function () {
    app.listen(PORT, function () {
        console.log("Server is running on http://localhost:".concat(PORT));
    });
}).catch(function (err) {
    console.error("Error during initialization: ", err);
});
