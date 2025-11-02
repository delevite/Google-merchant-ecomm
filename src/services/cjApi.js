
import axios from "axios";
import { refreshCJToken } from "./tokenRefresher.js";

export async function fetchCJProducts() {
  const token = process.env.CJ_ACCESS_TOKEN;

  try {
    const response = await axios.post(
      "https://developers.cjdropshipping.com/api2.0/v1/product/list",
      { pageNum: 1, pageSize: 10 },
      { headers: { "CJ-Access-Token": token } }
    );

    if (response.data.code === 403) {
      console.log("🔁 Token expired, refreshing...");
      const newToken = await refreshCJToken();

      const retry = await axios.post(
        "https://developers.cjdropshipping.com/api2.0/v1/product/list",
        { pageNum: 1, pageSize: 10 },
        { headers: { "CJ-Access-Token": newToken } }
      );

      return retry.data;
    }

    return response.data;
  } catch (err) {
    console.error("❌ CJ API Error:", err.message);
  }
}
