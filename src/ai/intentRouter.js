
import { fetchUserOrders, requestRefund } from "./orderReturnAssistant.js";
import { orderAndCouponHandler } from "./orderAndCouponAssistant.js";

export async function intentRouter(query, userEmail, token) {
  if (query.match(/return|refund/i)) {
    const orderNumber = query.match(/order\s+(\d+)/i)?.[1] || "unknown";
    const reason =
      query.split("because")[1]?.trim() ||
      "Customer requested refund via chat.";
    return await requestRefund(orderNumber, reason, userEmail);
  } else if (query.match(/my\s+orders|recent\s+orders/i)) {
    return await fetchUserOrders(userEmail, token);
  } else {
    return await orderAndCouponHandler(query, token);
  }
}
