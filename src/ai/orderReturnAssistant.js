
import axios from "axios";
import nodemailer from "nodemailer";

// ✅ Fetch user orders for summary
export async function fetchUserOrders(email, token) {
  try {
    const res = await axios.post(
      "https://developers.cjdropshipping.com/api2.0/v1/order/list",
      {
        pageNum: 1,
        pageSize: 5,
        email,
      },
      { headers: { Authorization: `Bearer ${token}` } }
    );

    if (res.data?.data?.list?.length) {
      const orders = res.data.data.list
        .map(
          (o) =>
            `#${o.orderNumber} - ${o.productName} (${o.orderStatus}) - ₦${o.orderAmount}`
        )
        .join("\n");
      return `📦 Your recent orders:\n${orders}`;
    }
    return "You don't have any recent orders yet.";
  } catch (err) {
    return "⚠️ Unable to fetch orders right now.";
  }
}

// ✅ Initiate return or refund
export async function requestRefund(orderNumber, reason, userEmail) {
  try {
    // Mock: in production, integrate with CJ API for refund creation
    const message = `Refund initiated for Order #${orderNumber}. Reason: ${reason}.`;

    // Notify admin
    const transporter = nodemailer.createTransport({
      service: "gmail",
      auth: {
        user: process.env.ADMIN_EMAIL,
        pass: process.env.ADMIN_PASS,
      },
    });

    await transporter.sendMail({
      from: process.env.ADMIN_EMAIL,
      to: process.env.ADMIN_EMAIL,
      subject: `Refund Request - Order #${orderNumber}`,
      text: `${userEmail} requested refund.\nReason: ${reason}`,
    });

    return `✅ Your refund request for Order #${orderNumber} has been sent!`;
  } catch (err) {
    return "❌ Could not process your refund request. Try again later.";
  }
}
