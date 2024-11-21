import { config } from "dotenv";
import { readFileSync } from "fs";
import {
  createThirdwebClient,
  getContract,
  sendAndConfirmTransaction,
} from "thirdweb";
import { polygonAmoy } from "thirdweb/chains";
import { deployERC721Contract } from "thirdweb/deploys";
import { lazyMint } from "thirdweb/extensions/erc721";
import { privateKeyToAccount } from "thirdweb/wallets";

import { inAppWallet, preAuthenticate } from "thirdweb/wallets/in-app";
 
const wallet = inAppWallet();

config();

const main = async () => {
  if (!process.env.WALLET_PRIVATE_KEY) {
    throw new Error("No private key found");
  }
  if (!process.env.THIRDWEB_SECRET_KEY) {
    throw new Error("No THIRDWEB_SECRET_KEY found");
  }
  try {
    const chain = polygonAmoy;
    const client = createThirdwebClient({
      secretKey: process.env.THIRDWEB_SECRET_KEY,
    });
    // sends a verification code to the provided email
    await preAuthenticate({
      client,
      strategy: "email",
      email: "example@example.com",
    });
    
    // login with the verification code
    const account = await wallet.connect({
      client,
      chain,
      strategy: "email",
      email: "example@example.com",
      verificationCode: "123456",
    });
    // const account = privateKeyToAccount({
    //   client,
    //   privateKey: process.env.WALLET_PRIVATE_KEY,
    // }); // private key account
    const address = ; // contract address
    console.log("Contract address: ", address);
    const contract = getContract({ address, chain, client });
    
    const transaction = ;

    const data = await sendAndConfirmTransaction({
      transaction,
      account,
    });
    console.log("Lazy minted successfully!");
    console.log(`Transaction hash: ${data.transactionHash}`);
  } catch (err) {
    console.error("Something went wrong: ", err);
  }
};

main();
