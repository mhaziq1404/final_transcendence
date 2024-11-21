// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract PongGameResults {
    struct GameResult {
        string player1; // Name of player 1
        string player2; // Name of player 2
        uint256 score1; // Score of player 1
        uint256 score2; // Score of player 2
        string winner;  // Name of the winner
        uint256 timestamp; // Timestamp of the game
    }

    GameResult[] public gameResults; // Array to store all game results

    // Event to emit whenever a new game result is stored
    event GameResultStored(
        string indexed player1,
        string indexed player2,
        uint256 score1,
        uint256 score2,
        string indexed winner,
        uint256 timestamp
    );

    // Function to store a new game result
    function storeGameResult(
        string memory _player1,
        string memory _player2,
        uint256 _score1,
        uint256 _score2,
        string memory _winner
    ) external {
        require(bytes(_player1).length > 0 && bytes(_player2).length > 0, "Invalid player names");
        require(keccak256(bytes(_winner)) == keccak256(bytes(_player1)) || keccak256(bytes(_winner)) == keccak256(bytes(_player2)), "Winner must be one of the players");

        GameResult memory newResult = GameResult({
            player1: _player1,
            player2: _player2,
            score1: _score1,
            score2: _score2,
            winner: _winner,
            timestamp: block.timestamp
        });

        gameResults.push(newResult);

        // Emit an event for the newly stored game result
        emit GameResultStored(_player1, _player2, _score1, _score2, _winner, block.timestamp);
    }

    // Function to retrieve the total number of stored game results
    function getGameResultsCount() external view returns (uint256) {
        return gameResults.length;
    }

    function getGameResults(uint256 startIndex, uint256 endIndex) external view returns (
        string[] memory player1s,
        string[] memory player2s,
        uint256[] memory score1s,
        uint256[] memory score2s,
        string[] memory winners,
        uint256[] memory timestamps
    ) {
        require(startIndex < gameResults.length, "Start index out of bounds");
        require(endIndex >= startIndex && endIndex < gameResults.length, "End index out of bounds");

        uint256 resultCount = endIndex - startIndex + 1;

        player1s = new string[](resultCount);
        player2s = new string[](resultCount);
        score1s = new uint256[](resultCount);
        score2s = new uint256[](resultCount);
        winners = new string[](resultCount);
        timestamps = new uint256[](resultCount);

        for (uint256 i = 0; i < resultCount; i++) {
            GameResult storage result = gameResults[startIndex + i];
            player1s[i] = result.player1;
            player2s[i] = result.player2;
            score1s[i] = result.score1;
            score2s[i] = result.score2;
            winners[i] = result.winner;
            timestamps[i] = result.timestamp;
        }
    }

    // Function to retrieve a specific game result by index
    function getGameResult(uint256 _index) external view returns (
        string memory player1,
        string memory player2,
        uint256 score1,
        uint256 score2,
        string memory winner,
        uint256 timestamp
    ) {
        require(_index < gameResults.length, "Invalid index");

        GameResult storage result = gameResults[_index];
        return (
            result.player1,
            result.player2,
            result.score1,
            result.score2,
            result.winner,
            result.timestamp
        );
    }
}
