
import axios from "axios";
import { generateAIResponse } from "./chatbotAssistant.js";

// ✅ Fetch order status from CJ Dropshipping
export async function getCJOrderStatus(orderNumber, token) {
  try {
    const res = await axios.post(
      "https://developers.cjdropshipping.com/api2.0/v1/order/getOrderByNumber",
      { orderNumber },
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (res.data?.data?.length) {
      const order = res.data.data[0];
      return `Order ${orderNumber} is currently *${order.orderStatus}* and expected to arrive around ${order.shipTime || "soon"}.`;
    }
    return `Sorry, no order found with number ${orderNumber}. Please double-check.`;
  } catch (err) {
    return "Couldn't fetch your order status at the moment. Try again later.";
  }
}

// ✅ Validate coupon code
export async function validateCoupon(code) {
  const validCoupons = {
    SAVE10: 10,
    FREEDELIVERY: 100,
    VIP15: 15,
  };
  if (validCoupons[code]) {
    return `🎉 Great! Your code *${code}* gives you ${validCoupons[code]}% off.`;
  }
  return `❌ Sorry, the code *${code}* is invalid or expired.`;
}

// ✅ Combined intent handler
export async function orderAndCouponHandler(query, token) {
  if (query.match(/order\s+\d+/i)) {
    const orderNumber = query.match(/order\s+(\d+)/i)[1];
    return await getCJOrderStatus(orderNumber, token);
  } else if (query.match(/coupon/i)) {
    const code = query.split(" ").pop().trim().toUpperCase();
    return await validateCoupon(code);
  } else {
    return await generateAIResponse(query);
  }
}
